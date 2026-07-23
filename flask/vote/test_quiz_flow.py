import os
import unittest
from datetime import timedelta
from pathlib import Path


os.environ["FLASK_ENV"] = "testing"

import vote as app_module  # noqa: E402
from models import (  # noqa: E402
    db,
    VotingSession,
    Question,
    Option,
    Participant,
    AnswerAttempt,
    ParticipantSessionState,
    QuestionStart,
)


ROOT = Path(__file__).resolve().parent


class QuizFlowTestCase(unittest.TestCase):
    def setUp(self):
        self.app = app_module.app
        self.app.config.update(TESTING=True)
        self.context = self.app.app_context()
        self.context.push()
        db.drop_all()
        db.create_all()

        self.voting_session = VotingSession(
            title="Missao institucional",
            description="Etapa cidadania",
        )
        self.question_one = Question(
            prompt="Qual alternativa esta correta?",
            position=1,
            time_limit_seconds=23,
            points_base=10,
        )
        self.question_one.options = [
            Option(label="Correta", position=1, is_correct=True),
            Option(label="Errada", position=2, is_correct=False),
        ]
        self.question_two = Question(
            prompt="Qual e a segunda correta?",
            position=2,
            time_limit_seconds=23,
            points_base=10,
        )
        self.question_two.options = [
            Option(label="Outra errada", position=1, is_correct=False),
            Option(label="Outra correta", position=2, is_correct=True),
        ]
        self.voting_session.questions = [self.question_one, self.question_two]
        self.participant = Participant(display_name="Pessoa Teste")
        db.session.add_all([self.voting_session, self.participant])
        db.session.commit()

        self.client = self.app.test_client()
        with self.client.session_transaction() as session:
            session["participant_id"] = self.participant.id
            session["session_id"] = self.voting_session.id

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.context.pop()

    @property
    def correct_option(self):
        return self.question_one.options[0]

    @property
    def wrong_option(self):
        return self.question_one.options[1]

    def start_question(self):
        response = self.client.get("/api/state")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["quiz"]["state"], "answering")
        return data

    def answer(self, option):
        return self.client.post(
            f"/api/questions/{self.question_one.id}/vote",
            json={"option_id": option.id},
        )

    def test_correct_answer_scores_base_plus_speed_bonus(self):
        self.start_question()

        response = self.answer(self.correct_option)
        data = response.get_json()

        self.assertEqual(response.status_code, 201)
        self.assertEqual(data["quiz"]["state"], "answered_correct")
        self.assertTrue(data["attempt"]["is_correct"])
        self.assertEqual(data["attempt"]["points_base"], 10)
        self.assertEqual(data["attempt"]["bonus_points"], 23)
        self.assertEqual(data["attempt"]["points_awarded"], 33)
        self.assertEqual(db.session.get(Participant, self.participant.id).score, 33)

    def test_incorrect_answer_reveals_correct_option_without_points(self):
        self.start_question()

        response = self.answer(self.wrong_option)
        data = response.get_json()

        self.assertEqual(response.status_code, 201)
        self.assertEqual(data["quiz"]["state"], "answered_incorrect")
        self.assertFalse(data["attempt"]["is_correct"])
        self.assertEqual(data["attempt"]["points_awarded"], 0)
        self.assertEqual(data["quiz"]["question"]["correct_option_id"], self.correct_option.id)

    def test_timeout_is_recorded_as_incorrect_idempotent_attempt(self):
        self.start_question()
        question_start = QuestionStart.query.filter_by(
            participant_id=self.participant.id,
            question_id=self.question_one.id,
        ).one()
        question_start.started_at = app_module._utcnow() - timedelta(seconds=30)
        db.session.commit()

        response = self.client.post(
            f"/api/questions/{self.question_one.id}/vote",
            json={"timeout": True},
        )
        data = response.get_json()

        self.assertEqual(response.status_code, 201)
        self.assertEqual(data["quiz"]["state"], "timed_out")
        self.assertTrue(data["attempt"]["timed_out"])
        self.assertFalse(data["attempt"]["is_correct"])
        self.assertIsNone(data["attempt"]["selected_option_id"])
        self.assertEqual(data["attempt"]["points_awarded"], 0)

    def test_bonus_boundaries_are_zero_and_time_limit(self):
        self.assertEqual(app_module._calculate_points(True, 10, 23, 0), (23, 33))
        self.assertEqual(app_module._calculate_points(True, 10, 23, 23), (0, 10))
        self.assertEqual(app_module._calculate_points(False, 10, 23, 0), (0, 0))

    def test_client_tampered_time_score_and_timeout_are_ignored(self):
        self.start_question()

        response = self.client.post(
            f"/api/questions/{self.question_one.id}/vote",
            json={
                "option_id": self.correct_option.id,
                "points_awarded": 9999,
                "bonus_points": 9999,
                "time_used_seconds": 0,
                "timeout": False,
            },
        )
        data = response.get_json()

        self.assertEqual(response.status_code, 201)
        self.assertEqual(data["attempt"]["points_awarded"], 33)
        self.assertNotEqual(data["attempt"]["points_awarded"], 9999)

    def test_option_from_another_question_is_rejected(self):
        self.start_question()
        foreign_option = self.question_two.options[1]

        response = self.client.post(
            f"/api/questions/{self.question_one.id}/vote",
            json={"option_id": foreign_option.id},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(AnswerAttempt.query.count(), 0)

    def test_double_click_replays_are_idempotent_and_unique(self):
        self.start_question()

        first = self.answer(self.correct_option)
        second = self.answer(self.correct_option)
        third = self.answer(self.wrong_option)

        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(third.status_code, 200)
        self.assertEqual(AnswerAttempt.query.count(), 1)
        self.assertEqual(db.session.get(Participant, self.participant.id).score, 33)
        constraints = AnswerAttempt.__table__.constraints
        self.assertTrue(any("participant_question_attempt" in item.name for item in constraints if item.name))

    def test_reload_does_not_restart_deadline(self):
        self.start_question()
        first_start = QuestionStart.query.filter_by(
            participant_id=self.participant.id,
            question_id=self.question_one.id,
        ).one().started_at

        response = self.client.get("/api/state")
        self.assertEqual(response.status_code, 200)
        second_start = QuestionStart.query.filter_by(
            participant_id=self.participant.id,
            question_id=self.question_one.id,
        ).one().started_at

        self.assertEqual(first_start, second_start)

    def test_manual_advance_moves_to_next_question_and_starts_deadline(self):
        self.start_question()
        self.answer(self.correct_option)

        response = self.client.post("/api/quiz/advance", json={"source": "manual"})
        data = response.get_json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["quiz"]["state"], "answering")
        self.assertEqual(data["quiz"]["question_index"], 2)
        self.assertEqual(data["quiz"]["question"]["id"], self.question_two.id)
        self.assertIsNotNone(
            QuestionStart.query.filter_by(
                participant_id=self.participant.id,
                question_id=self.question_two.id,
            ).first()
        )

    def test_auto_advance_uses_same_server_gate(self):
        self.start_question()
        self.answer(self.correct_option)

        response = self.client.post("/api/quiz/advance", json={"source": "auto"})
        data = response.get_json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["quiz"]["question_index"], 2)

    def test_review_mode_does_not_auto_advance(self):
        self.finish_session()

        response = self.client.post("/api/quiz/advance", json={"source": "auto"})
        data = response.get_json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["quiz"]["state"], "completed")
        self.assertEqual(data["quiz"]["mode"], "review")
        progress = ParticipantSessionState.query.filter_by(
            participant_id=self.participant.id,
            session_id=self.voting_session.id,
        ).one()
        self.assertIsNone(progress.current_question_id)

    def test_last_question_finalizes_stage(self):
        data = self.finish_session()

        self.assertEqual(data["quiz"]["state"], "completed")
        self.assertEqual(data["quiz"]["mode"], "review")
        self.assertEqual(len(data["quiz"]["questions"]), 2)
        self.assertEqual(data["quiz"]["answered_count"], 2)

    def finish_session(self):
        self.start_question()
        self.answer(self.correct_option)
        self.client.post("/api/quiz/advance", json={"source": "manual"})
        second_correct = self.question_two.options[1]
        self.client.post(
            f"/api/questions/{self.question_two.id}/vote",
            json={"option_id": second_correct.id},
        )
        response = self.client.post("/api/quiz/advance", json={"source": "manual"})
        self.assertEqual(response.status_code, 200)
        return response.get_json()


class FrontendContractTestCase(unittest.TestCase):
    def setUp(self):
        self.js = (ROOT / "static/js/app.js").read_text()
        self.css = (ROOT / "static/css/style.css").read_text()

    def test_state_machine_names_are_explicit(self):
        for state in [
            "loading",
            "answering",
            "submitting",
            "answered_correct",
            "answered_incorrect",
            "timed_out",
            "advancing",
            "completed",
            "error",
        ]:
            self.assertIn(state, self.js)

    def test_keyboard_navigation_uses_native_buttons_and_focus_styles(self):
        self.assertIn('class="choice-option', self.js)
        self.assertIn('type="button"', self.js)
        self.assertIn(":focus-visible", self.css)
        self.assertIn("min-height: 56px", self.css)

    def test_responsive_contract_has_required_breakpoints_and_no_horizontal_scroll(self):
        for snippet in [
            "overflow-x: hidden",
            "@media (max-width: 374.98px)",
            "@media (min-width: 375px)",
            "@media (min-width: 768px)",
            "@media (min-width: 1024px)",
            "@media (min-width: 1440px)",
            "orientation: landscape",
        ]:
            self.assertIn(snippet, self.css)

    def test_reduced_motion_is_supported_in_css_and_js(self):
        self.assertIn("prefers-reduced-motion: reduce", self.css)
        self.assertIn("prefers-reduced-motion: reduce", self.js)

    def test_feedback_countdown_and_review_mode_are_present(self):
        self.assertIn("advance_delay_seconds", self.js)
        self.assertIn("Pausar automatico", self.js)
        self.assertIn("Modo de revisao", self.js)


if __name__ == "__main__":
    unittest.main()
