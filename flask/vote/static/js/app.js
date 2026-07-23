document.addEventListener("DOMContentLoaded", () => {
    const root = document.querySelector("[data-app]");
    if (!root) {
        return;
    }

    const participantPanel = document.querySelector('[data-role="participant"]');
    const adminPanel = document.querySelector('[data-role="admin"]');

    if (participantPanel) {
        initParticipant(participantPanel);
    }

    if (adminPanel) {
        initAdmin(adminPanel);
    }
});


const QUIZ_STATES = Object.freeze({
    LOADING: "loading",
    ANSWERING: "answering",
    SUBMITTING: "submitting",
    ANSWERED_CORRECT: "answered_correct",
    ANSWERED_INCORRECT: "answered_incorrect",
    TIMED_OUT: "timed_out",
    ADVANCING: "advancing",
    COMPLETED: "completed",
    ERROR: "error",
});

const TIMER_MILESTONES = new Set([10, 5, 3, 2, 1]);
const CARD_THEMES = [
    "poll-soft-blue",
    "poll-soft-green",
    "poll-soft-purple",
    "poll-soft-gray",
];


function themeFor(index) {
    return CARD_THEMES[index % CARD_THEMES.length];
}


function initParticipant(panel) {
    const stateUrl = panel.dataset.stateUrl;
    const advanceUrl = panel.dataset.advanceUrl;
    const stateTarget = document.getElementById("participant-state");
    const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");

    const appState = {
        status: QUIZ_STATES.LOADING,
        data: null,
        serverOffsetMs: 0,
        timerHandle: null,
        advanceHandle: null,
        advanceDeadlineMs: 0,
        autoAdvancePaused: false,
        submitting: false,
        announcedTimerSecond: null,
    };

    const setStatus = (status) => {
        appState.status = status;
        panel.dataset.quizState = status;
    };

    const clearTimer = () => {
        if (appState.timerHandle) {
            window.clearTimeout(appState.timerHandle);
            appState.timerHandle = null;
        }
    };

    const clearAdvanceTimer = () => {
        if (appState.advanceHandle) {
            window.clearTimeout(appState.advanceHandle);
            appState.advanceHandle = null;
        }
    };

    const refresh = async () => {
        clearTimer();
        clearAdvanceTimer();
        setStatus(QUIZ_STATES.LOADING);
        try {
            const response = await fetch(stateUrl, {
                headers: { Accept: "application/json" },
                cache: "no-store",
            });
            render(await response.json());
        } catch (error) {
            renderError("Nao foi possivel carregar o quiz.");
        }
    };

    const render = (data) => {
        appState.data = data;
        appState.submitting = false;
        appState.announcedTimerSecond = null;
        syncServerOffset(data);
        clearTimer();
        clearAdvanceTimer();

        if (!data.session) {
            setStatus(QUIZ_STATES.LOADING);
            stateTarget.innerHTML = renderWaiting();
            return;
        }

        if (!data.quiz || data.quiz.state === QUIZ_STATES.COMPLETED) {
            setStatus(QUIZ_STATES.COMPLETED);
            stateTarget.innerHTML = renderCompleted(data);
            return;
        }

        const status = normalizeStatus(data.quiz.state);
        setStatus(status);
        stateTarget.innerHTML = renderQuiz(data, status, prefersReducedMotion.matches);

        if (status === QUIZ_STATES.ANSWERING) {
            startQuestionTimer();
            focusFirstChoice();
            return;
        }

        if (isFeedbackStatus(status)) {
            focusFeedback();
            startAdvanceCountdown();
        }
    };

    const renderError = (message) => {
        setStatus(QUIZ_STATES.ERROR);
        stateTarget.innerHTML = `
            <div class="quiz-empty-state quiz-error" role="alert">
                ${escapeHtml(message)}
            </div>
        `;
    };

    const syncServerOffset = (data) => {
        const serverNow = Date.parse(data.server_now || "");
        appState.serverOffsetMs = Number.isFinite(serverNow) ? serverNow - Date.now() : 0;
    };

    const serverNow = () => Date.now() + appState.serverOffsetMs;

    const currentQuestion = () => appState.data && appState.data.quiz
        ? appState.data.quiz.question
        : null;

    const remainingMs = () => {
        const question = currentQuestion();
        if (!question || !question.deadline_at) {
            return 0;
        }
        return Math.max(0, Date.parse(question.deadline_at) - serverNow());
    };

    const startQuestionTimer = () => {
        const update = () => {
            if (appState.status !== QUIZ_STATES.ANSWERING || appState.submitting) {
                return;
            }

            const question = currentQuestion();
            if (!question) {
                return;
            }

            const limit = Math.max(Number(question.time_limit_seconds) || 1, 1);
            const ms = remainingMs();
            const seconds = Math.max(0, Math.ceil(ms / 1000));
            const ratio = Math.max(0, Math.min(ms / (limit * 1000), 1));
            updateTimerDisplay(seconds, ratio, limit);

            if (seconds <= 0) {
                announceTimer("Tempo esgotado.");
                submitAnswer({ timeout: true });
                return;
            }

            appState.timerHandle = window.setTimeout(update, prefersReducedMotion.matches ? 1000 : 250);
        };

        update();
    };

    const updateTimerDisplay = (seconds, ratio, limit) => {
        const timerValue = stateTarget.querySelector("[data-timer-value]");
        const timerBar = stateTarget.querySelector("[data-timer-bar]");
        const timerBox = stateTarget.querySelector("[data-timer]");
        const timerLive = stateTarget.querySelector("[data-timer-live]");

        if (timerValue) {
            timerValue.textContent = String(seconds);
        }

        if (timerBar) {
            const percent = Math.round(ratio * 100);
            timerBar.style.setProperty("--time-scale", String(ratio));
            timerBar.setAttribute("aria-valuenow", String(percent));
        }

        if (timerBox) {
            timerBox.dataset.tone = timerTone(seconds, limit);
        }

        if (timerLive && TIMER_MILESTONES.has(seconds) && appState.announcedTimerSecond !== seconds) {
            appState.announcedTimerSecond = seconds;
            timerLive.textContent = `${seconds} segundos restantes.`;
        }
    };

    const announceTimer = (message) => {
        const timerLive = stateTarget.querySelector("[data-timer-live]");
        if (timerLive) {
            timerLive.textContent = message;
        }
    };

    const submitAnswer = async ({ optionId = null, timeout = false } = {}) => {
        const question = currentQuestion();
        if (!question || appState.submitting || appState.status === QUIZ_STATES.SUBMITTING) {
            return;
        }

        appState.submitting = true;
        setStatus(QUIZ_STATES.SUBMITTING);
        disableChoices();
        clearTimer();

        try {
            const body = timeout
                ? { timeout: true }
                : { option_id: Number(optionId) };
            const response = await fetch(`/api/questions/${question.id}/vote`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    Accept: "application/json",
                },
                body: JSON.stringify(body),
            });
            const data = await response.json();
            if (!response.ok && response.status !== 409) {
                renderError(data.error || "Nao foi possivel registrar a resposta.");
                return;
            }
            render(data);
        } catch (error) {
            renderError("Nao foi possivel registrar a resposta.");
        }
    };

    const advanceQuiz = async (source) => {
        if (appState.status === QUIZ_STATES.ADVANCING) {
            return;
        }
        clearAdvanceTimer();
        setStatus(QUIZ_STATES.ADVANCING);

        try {
            const response = await fetch(advanceUrl, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    Accept: "application/json",
                },
                body: JSON.stringify({ source }),
            });
            render(await response.json());
        } catch (error) {
            renderError("Nao foi possivel avancar.");
        }
    };

    const startAdvanceCountdown = () => {
        const quiz = appState.data.quiz;
        if (!quiz || quiz.mode !== "active") {
            return;
        }

        const delay = Math.max(Number(quiz.advance_delay_seconds) || 10, 1);
        appState.advanceDeadlineMs = Date.now() + delay * 1000;

        const tick = () => {
            if (!isFeedbackStatus(appState.status)) {
                return;
            }

            const remaining = Math.max(0, Math.ceil((appState.advanceDeadlineMs - Date.now()) / 1000));
            updateAdvanceButton(remaining);

            if (remaining <= 0) {
                if (!appState.autoAdvancePaused) {
                    advanceQuiz("auto");
                }
                return;
            }

            appState.advanceHandle = window.setTimeout(tick, 250);
        };

        tick();
    };

    const updateAdvanceButton = (seconds) => {
        const button = stateTarget.querySelector("[data-action='advance']");
        if (!button) {
            return;
        }
        const quiz = appState.data.quiz;
        const label = quiz.is_last_question ? "Finalizar etapa" : "Proxima pergunta";
        button.querySelector("[data-advance-label]").textContent = appState.autoAdvancePaused
            ? label
            : `${label} (${seconds}s)`;
    };

    const disableChoices = () => {
        stateTarget.querySelectorAll("[data-option-id]").forEach((button) => {
            button.disabled = true;
        });
    };

    const focusFirstChoice = () => {
        const firstChoice = stateTarget.querySelector("[data-option-id]");
        if (firstChoice) {
            firstChoice.focus({ preventScroll: true });
        }
    };

    const focusFeedback = () => {
        window.requestAnimationFrame(() => {
            const feedback = stateTarget.querySelector("[data-feedback-panel]");
            if (feedback) {
                feedback.focus({ preventScroll: false });
            }
        });
    };

    panel.addEventListener("click", (event) => {
        const optionButton = event.target.closest("[data-option-id]");
        if (optionButton && appState.status === QUIZ_STATES.ANSWERING) {
            submitAnswer({ optionId: optionButton.dataset.optionId });
            return;
        }

        const actionButton = event.target.closest("[data-action]");
        if (!actionButton) {
            return;
        }

        if (actionButton.dataset.action === "back") {
            if (window.history.length > 1) {
                window.history.back();
            } else {
                window.location.href = "/";
            }
            return;
        }

        if (actionButton.dataset.action === "advance") {
            advanceQuiz("manual");
            return;
        }

        if (actionButton.dataset.action === "toggle-auto") {
            appState.autoAdvancePaused = !appState.autoAdvancePaused;
            actionButton.setAttribute("aria-pressed", String(appState.autoAdvancePaused));
            actionButton.querySelector("[data-pause-label]").textContent = appState.autoAdvancePaused
                ? "Retomar automatico"
                : "Pausar automatico";
            if (!appState.autoAdvancePaused) {
                const delay = Math.max(Number(appState.data.quiz.advance_delay_seconds) || 10, 1);
                appState.advanceDeadlineMs = Date.now() + delay * 1000;
                startAdvanceCountdown();
            } else {
                clearAdvanceTimer();
                updateAdvanceButton(0);
            }
        }
    });

    document.addEventListener("visibilitychange", () => {
        if (!document.hidden && appState.status === QUIZ_STATES.ANSWERING) {
            clearTimer();
            startQuestionTimer();
        }
    });

    window.addEventListener("focus", () => {
        if (appState.status === QUIZ_STATES.ANSWERING) {
            clearTimer();
            startQuestionTimer();
        }
    });

    refresh();
}


function renderWaiting() {
    return `
        <div class="quiz-empty-state" role="status">
            <div class="quiz-empty-title">Aguardando entrada na sala</div>
            <p>Entre por um QR code ativo para iniciar o quiz.</p>
            <a class="btn btn-primary rounded-pill px-4" href="/admin">Abrir admin</a>
        </div>
    `;
}


function renderQuiz(data, status, reducedMotion) {
    const quiz = data.quiz;
    const question = quiz.question;
    const attempt = question.attempt;
    const answered = isFeedbackStatus(status);
    const progress = Math.max(0, Math.min(Number(quiz.progress_percent) || 0, 100));
    const remaining = Math.max(0, Number(question.remaining_seconds) || 0);
    const timeRatio = Math.max(0, Math.min(remaining / Math.max(question.time_limit_seconds, 1), 1));
    const missionName = data.session.description || data.session.title;

    return `
        <article class="quiz-shell-inner" data-view-state="${status}">
            ${renderQuizHeader(data)}
            <section class="mission-strip" aria-label="Missao atual">
                <span class="mission-icon" aria-hidden="true">${icon("mission")}</span>
                <span>${escapeHtml(missionName)}</span>
            </section>
            <section class="quiz-progress-block" aria-label="Progresso da etapa">
                <div class="progress-copy">
                    <span>Progresso: ${quiz.question_index}/${quiz.question_count}</span>
                    <strong>${progress}%</strong>
                </div>
                <div
                    class="quiz-progress-track"
                    role="progressbar"
                    aria-valuemin="0"
                    aria-valuemax="100"
                    aria-valuenow="${progress}"
                    aria-label="Progresso"
                >
                    <span class="quiz-progress-fill" style="--progress-scale:${progress / 100}"></span>
                </div>
            </section>
            <section class="timer-panel" data-timer data-tone="${timerTone(remaining, question.time_limit_seconds)}">
                <div>
                    <div class="timer-value" data-timer-value aria-hidden="true">${remaining}</div>
                    <div class="timer-label">Tempo para responder</div>
                    <div class="visually-hidden" role="status" aria-live="polite" data-timer-live></div>
                </div>
                <div
                    class="timer-track"
                    role="progressbar"
                    aria-valuemin="0"
                    aria-valuemax="100"
                    aria-valuenow="${Math.round(timeRatio * 100)}"
                    aria-label="Tempo restante"
                >
                    <span
                        class="timer-fill"
                        data-timer-bar
                        style="--time-scale:${timeRatio}"
                    ></span>
                </div>
            </section>
            <section class="question-card" aria-labelledby="question-title">
                <div class="question-kicker">Pergunta ${quiz.question_index}</div>
                <h1 id="question-title">${escapeHtml(question.prompt)}</h1>
                <div class="choice-list" role="group" aria-label="Alternativas">
                    ${question.options.map((option, index) => renderChoice(option, index, answered, attempt)).join("")}
                </div>
            </section>
            ${answered ? renderFeedback(data, status) : ""}
            <footer class="quiz-footer" aria-label="Resumo do desempenho">
                <div>
                    <span>Respondidas</span>
                    <strong>${quiz.answered_count}</strong>
                </div>
                <div>
                    <span>Corretas</span>
                    <strong>${quiz.correct_count}</strong>
                </div>
                <div>
                    <span>Taxa de acerto</span>
                    <strong>${quiz.accuracy_percent}%</strong>
                </div>
            </footer>
            ${reducedMotion ? '<span class="visually-hidden">Movimento reduzido ativo.</span>' : ""}
        </article>
    `;
}


function renderQuizHeader(data) {
    const quiz = data.quiz;
    return `
        <header class="quiz-header">
            <button class="quiz-back-button" type="button" data-action="back">
                ${icon("arrow-left")}
                <span>Voltar</span>
            </button>
            <div class="quiz-title-block">
                <div class="quiz-title">${escapeHtml(data.session.title)}</div>
                <div class="quiz-subtitle">${escapeHtml(data.participant.display_name)}</div>
            </div>
            <div class="quiz-header-meta" aria-label="Status do quiz">
                <span>Pergunta ${quiz.question_index} de ${quiz.question_count}</span>
                <strong>${quiz.score} pts</strong>
            </div>
        </header>
    `;
}


function renderChoice(option, index, answered, attempt) {
    const isSelected = attempt && attempt.selected_option_id === option.id;
    const isCorrect = Boolean(option.is_correct);
    const stateClass = answered
        ? isCorrect
            ? "is-correct"
            : isSelected
                ? "is-wrong"
                : "is-neutral"
        : "";
    const iconName = answered
        ? isCorrect
            ? "check"
            : isSelected
                ? "x"
                : "circle"
        : "circle";
    const stateText = answered
        ? isCorrect
            ? "Correta"
            : isSelected
                ? "Selecionada"
                : "Nao selecionada"
        : `Alternativa ${index + 1}`;

    return `
        <button
            class="choice-option ${stateClass}"
            type="button"
            data-option-id="${option.id}"
            ${answered ? "disabled" : ""}
        >
            <span class="choice-state-icon" aria-hidden="true">${icon(iconName)}</span>
            <span class="choice-label">${escapeHtml(option.label)}</span>
            <span class="choice-state-text">${stateText}</span>
        </button>
    `;
}


function renderFeedback(data, status) {
    const quiz = data.quiz;
    const question = quiz.question;
    const attempt = question.attempt || {};
    const isCorrect = status === QUIZ_STATES.ANSWERED_CORRECT;
    const isTimeout = status === QUIZ_STATES.TIMED_OUT;
    const role = isCorrect ? "status" : "alert";
    const title = isTimeout
        ? "Tempo esgotado"
        : isCorrect
            ? "Resposta correta"
            : "Resposta incorreta";
    const message = isTimeout
        ? "O prazo terminou e a pergunta foi marcada como incorreta."
        : isCorrect
            ? "Voce recebeu pontos-base e bonus de velocidade."
            : "A correta ficou destacada para revisao.";

    return `
        <aside
            class="feedback-panel ${isCorrect ? "feedback-success" : "feedback-error"}"
            role="${role}"
            tabindex="-1"
            data-feedback-panel
        >
            <div class="feedback-heading">
                <span aria-hidden="true">${icon(isCorrect ? "check" : "x")}</span>
                <div>
                    <h2>${title}</h2>
                    <p>${message}</p>
                </div>
            </div>
            <div class="feedback-stats">
                <div>
                    <span>Pontos-base</span>
                    <strong>${attempt.points_base || 0}</strong>
                </div>
                <div>
                    <span>Bonus</span>
                    <strong>${attempt.bonus_points || 0}</strong>
                </div>
                <div>
                    <span>Tempo usado</span>
                    <strong>${attempt.time_used_seconds || 0}s</strong>
                </div>
            </div>
            <div class="feedback-actions">
                <button class="btn btn-primary rounded-pill px-4" type="button" data-action="advance">
                    ${icon(quiz.is_last_question ? "flag" : "arrow-right")}
                    <span data-advance-label>${quiz.is_last_question ? "Finalizar etapa" : "Proxima pergunta"} (${quiz.advance_delay_seconds}s)</span>
                </button>
                <button
                    class="btn btn-outline-secondary rounded-pill px-4"
                    type="button"
                    data-action="toggle-auto"
                    aria-pressed="false"
                >
                    ${icon("pause")}
                    <span data-pause-label>Pausar automatico</span>
                </button>
            </div>
        </aside>
    `;
}


function renderCompleted(data) {
    const quiz = data.quiz || {};
    const questions = quiz.questions || [];
    return `
        <article class="quiz-shell-inner" data-view-state="completed">
            <header class="quiz-header">
                <button class="quiz-back-button" type="button" data-action="back">
                    ${icon("arrow-left")}
                    <span>Voltar</span>
                </button>
                <div class="quiz-title-block">
                    <div class="quiz-title">${escapeHtml(data.session.title)}</div>
                    <div class="quiz-subtitle">Modo de revisao</div>
                </div>
                <div class="quiz-header-meta">
                    <span>Etapa finalizada</span>
                    <strong>${quiz.score || 0} pts</strong>
                </div>
            </header>
            <section class="mission-strip" aria-label="Missao finalizada">
                <span class="mission-icon" aria-hidden="true">${icon("flag")}</span>
                <span>${escapeHtml(data.session.description || data.session.title)}</span>
            </section>
            <section class="completion-panel" role="status" tabindex="-1">
                <h1>Etapa concluida</h1>
                <div class="quiz-footer completion-stats" aria-label="Resumo final">
                    <div>
                        <span>Respondidas</span>
                        <strong>${quiz.answered_count || 0}</strong>
                    </div>
                    <div>
                        <span>Corretas</span>
                        <strong>${quiz.correct_count || 0}</strong>
                    </div>
                    <div>
                        <span>Taxa de acerto</span>
                        <strong>${quiz.accuracy_percent || 0}%</strong>
                    </div>
                </div>
            </section>
            <section class="review-list" aria-label="Revisao das perguntas">
                ${questions.map((question) => renderReviewQuestion(question)).join("")}
            </section>
        </article>
    `;
}


function renderReviewQuestion(question) {
    const attempt = question.attempt || {};
    return `
        <article class="review-question">
            <div class="question-kicker">Pergunta ${question.position}</div>
            <h2>${escapeHtml(question.prompt)}</h2>
            <div class="choice-list is-review">
                ${question.options.map((option, index) => renderChoice(option, index, true, attempt)).join("")}
            </div>
        </article>
    `;
}


function timerTone(seconds, limit) {
    if (seconds <= 5 || seconds <= Math.ceil(limit * 0.25)) {
        return "danger";
    }
    if (seconds <= 10 || seconds <= Math.ceil(limit * 0.5)) {
        return "warning";
    }
    return "safe";
}


function normalizeStatus(status) {
    return Object.values(QUIZ_STATES).includes(status) ? status : QUIZ_STATES.ERROR;
}


function isFeedbackStatus(status) {
    return [
        QUIZ_STATES.ANSWERED_CORRECT,
        QUIZ_STATES.ANSWERED_INCORRECT,
        QUIZ_STATES.TIMED_OUT,
    ].includes(status);
}


function initAdmin(panel) {
    const stateUrl = panel.dataset.stateUrl;
    const sessionForm = document.getElementById("session-form");
    const questionForm = document.getElementById("question-form");
    const optionsList = document.getElementById("options-list");
    const sessionPicker = document.getElementById("session-picker");
    const qrImage = document.getElementById("qr-image");
    const qrBaseUrlInput = document.getElementById("qr-base-url");
    const saveQrBaseButton = document.getElementById("save-qr-base");
    const useCurrentHostButton = document.getElementById("use-current-host");
    const clearQrBaseButton = document.getElementById("clear-qr-base");
    const openTestParticipantButton = document.getElementById("open-test-participant");
    const joinLink = document.getElementById("join-link");
    const adminState = document.getElementById("admin-state");
    const addOptionButton = document.getElementById("add-option");
    let sessionsCache = [];
    const storageKey = "vote-qr-base-url";

    const isPrivateHost = (hostname) => {
        return (
            hostname === "localhost" ||
            hostname === "127.0.0.1" ||
            hostname === "::1" ||
            hostname.endsWith(".local") ||
            /^10\./.test(hostname) ||
            /^192\.168\./.test(hostname) ||
            /^172\.(1[6-9]|2\d|3[0-1])\./.test(hostname)
        );
    };

    const loadQrBaseUrl = () => {
        try {
            return window.localStorage.getItem(storageKey) || "";
        } catch (error) {
            return "";
        }
    };

    const saveQrBaseUrl = (value) => {
        try {
            window.localStorage.setItem(storageKey, value);
        } catch (error) {
            return;
        }
    };

    const clearQrBaseUrl = () => {
        try {
            window.localStorage.removeItem(storageKey);
        } catch (error) {
            return;
        }
    };

    const normalizeBaseUrl = (value) => {
        const trimmed = value.trim();
        if (!trimmed) {
            return "";
        }

        try {
            const url = new URL(trimmed);
            if (url.protocol === "https:" && isPrivateHost(url.hostname)) {
                url.protocol = "http:";
            }
            return url.toString();
        } catch (error) {
            return trimmed;
        }
    };

    const addOptionField = (value = "", isCorrect = false) => {
        const index = optionsList.children.length;
        const row = document.createElement("div");
        row.className = "option-editor-row";
        row.innerHTML = `
            <label class="correct-radio">
                <input
                    type="radio"
                    name="correct_option"
                    value="${index}"
                    ${isCorrect ? "checked" : ""}
                >
                <span>Correta</span>
            </label>
            <input
                class="form-control rounded-4"
                name="option"
                value="${escapeAttribute(value)}"
                placeholder="Answer option"
            >
        `;
        optionsList.appendChild(row);
    };

    const resetOptionFields = () => {
        optionsList.innerHTML = "";
        addOptionField("Yes", true);
        addOptionField("No");
    };

    resetOptionFields();
    addOptionButton.addEventListener("click", () => addOptionField());

    const storedBaseUrl = loadQrBaseUrl();
    qrBaseUrlInput.value = normalizeBaseUrl(storedBaseUrl);
    saveQrBaseButton.addEventListener("click", () => {
        const normalized = normalizeBaseUrl(qrBaseUrlInput.value);
        if (normalized) {
            saveQrBaseUrl(normalized);
        } else {
            clearQrBaseUrl();
        }
        refresh();
    });
    useCurrentHostButton.addEventListener("click", () => {
        qrBaseUrlInput.value = normalizeBaseUrl(window.location.origin);
        saveQrBaseUrl(qrBaseUrlInput.value);
        refresh();
    });
    clearQrBaseButton.addEventListener("click", () => {
        qrBaseUrlInput.value = "";
        clearQrBaseUrl();
        refresh();
    });
    openTestParticipantButton.addEventListener("click", () => {
        const selectedSession = sessionsCache.find((item) => String(item.id) === String(sessionPicker.value)) || sessionsCache[0];
        if (!selectedSession) {
            return;
        }

        const joinUrl = buildJoinUrl(selectedSession);
        const opened = window.open(joinUrl, "_blank", "noopener");
        if (!opened) {
            window.location.href = joinUrl;
        }
    });

    const render = (state) => {
        const sessions = state.sessions || [];
        sessionsCache = sessions;

        sessionPicker.innerHTML = sessions.map((session) => `
            <option value="${session.id}">${escapeHtml(session.title)}</option>
        `).join("");

        if (sessions.length === 0) {
            qrImage.removeAttribute("src");
            joinLink.textContent = "Create a session to generate a QR join code.";
            adminState.innerHTML = `
                <div class="text-secondary py-3">
                    No sessions yet. Use the form above to create the first voting room.
                </div>
            `;
            return;
        }

        const selectedSession = sessions.find((item) => String(item.id) === String(sessionPicker.value)) || sessions[0];
        sessionPicker.value = selectedSession.id;
        updateQrPreview(selectedSession);

        adminState.innerHTML = sessions.map((session, sessionIndex) => {
            const sessionTheme = themeFor(sessionIndex);
            const questionMarkup = session.questions.length
                ? session.questions.map((question, questionIndex) => `
                    <article class="card question-card border-0 shadow-sm mb-3 overflow-hidden">
                        <div class="card-header ${themeFor(questionIndex)} border-0 py-3">
                            <div class="d-flex justify-content-between align-items-start gap-3">
                                <div>
                                    <div class="small text-uppercase fw-semibold opacity-75 mb-1">Question ${question.position}</div>
                                    <h3 class="h6 fw-semibold mb-1">${escapeHtml(question.prompt)}</h3>
                                    <div class="small opacity-75">
                                        ${question.total_answers} answer${question.total_answers === 1 ? "" : "s"} total
                                        · ${question.points_base} pts
                                        · ${question.time_limit_seconds}s
                                    </div>
                                </div>
                                <div class="d-flex gap-2 flex-wrap justify-content-end">
                                    <span class="badge rounded-pill text-bg-light text-dark">${question.is_open ? "Open" : "Closed"}</span>
                                </div>
                            </div>
                        </div>
                        <div class="card-body bg-white p-3">
                            <div class="vstack gap-2">
                                ${question.options.map((option) => `
                                    <div>
                                        <div class="d-flex justify-content-between gap-2 small mb-1">
                                            <strong>${escapeHtml(option.label)}</strong>
                                            <span>
                                                ${option.is_correct ? "Correct · " : ""}
                                                ${option.answers} answer${option.answers === 1 ? "" : "s"} · ${option.percent}%
                                            </span>
                                        </div>
                                        <div class="progress vote-result">
                                            <div class="progress-bar" style="width:${option.percent}%"></div>
                                        </div>
                                    </div>
                                `).join("")}
                            </div>
                            <div class="d-flex flex-wrap gap-2 mt-3">
                                <button class="btn btn-outline-secondary btn-sm rounded-pill" type="button" data-toggle-question="${question.id}">
                                    ${question.is_open ? "Close question" : "Open question"}
                                </button>
                                <button class="btn btn-outline-danger btn-sm rounded-pill" type="button" data-delete-question="${question.id}">
                                    Delete question
                                </button>
                            </div>
                        </div>
                    </article>
                `).join("")
                : `<div class="text-secondary py-2">No questions have been added yet.</div>`;

            return `
                <article class="card session-card border-0 shadow-sm mb-3 overflow-hidden">
                    <div class="card-header ${sessionTheme} border-0 py-3 py-lg-4">
                        <div class="d-flex justify-content-between align-items-start gap-3">
                            <div class="text-white">
                                <div class="small text-uppercase fw-semibold opacity-75 mb-1">Session ${session.id}</div>
                                <h3 class="h5 fw-semibold mb-2">${escapeHtml(session.title)}</h3>
                                <p class="mb-0 opacity-75">${escapeHtml(session.description || "No description provided.")}</p>
                            </div>
                            <div class="d-flex flex-column align-items-end gap-2">
                                <span class="badge rounded-pill text-bg-light text-dark">${session.is_active ? "Active" : "Closed"}</span>
                                <button class="btn btn-light btn-sm rounded-pill" type="button" data-delete-session="${session.id}">
                                    Delete session
                                </button>
                            </div>
                        </div>
                        <div class="d-flex flex-wrap gap-2 align-items-center mt-3 text-white-50 small">
                            <span class="badge rounded-pill text-bg-light text-dark">${session.questions.length} question${session.questions.length === 1 ? "" : "s"}</span>
                            <span class="session-join">${escapeHtml(session.join_url)}</span>
                        </div>
                    </div>
                    <div class="card-body bg-white p-3 p-lg-4">
                        ${questionMarkup}
                    </div>
                </article>
            `;
        }).join("");
    };

    const updateQrPreview = (session) => {
        const joinUrl = buildJoinUrl(session);
        const encodedUrl = encodeURIComponent(joinUrl);
        qrImage.src = `https://api.qrserver.com/v1/create-qr-code/?size=240x240&data=${encodedUrl}`;
        qrImage.alt = `QR code for ${session.title}`;
        joinLink.innerHTML = `<span class="fw-semibold">Join link:</span> ${escapeHtml(joinUrl)}`;
    };

    const buildJoinUrl = (session) => {
        const baseOverride = normalizeBaseUrl(qrBaseUrlInput.value);
        if (!baseOverride) {
            return session.join_url;
        }

        try {
            return new URL(`/join/${session.join_token}`, baseOverride).toString();
        } catch (error) {
            return session.join_url;
        }
    };

    sessionPicker.addEventListener("change", () => {
        const selected = sessionsCache.find((item) => String(item.id) === String(sessionPicker.value));
        if (selected) {
            updateQrPreview(selected);
        }
    });

    sessionForm.addEventListener("submit", async (event) => {
        event.preventDefault();
        const formData = new FormData(sessionForm);
        const response = await fetch("/api/sessions", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                Accept: "application/json",
            },
            body: JSON.stringify({
                title: formData.get("title"),
                description: formData.get("description"),
            }),
        });

        if (response.ok) {
            sessionForm.reset();
            await refresh();
        }
    });

    questionForm.addEventListener("submit", async (event) => {
        event.preventDefault();
        const sessionId = sessionPicker.value;
        if (!sessionId) {
            return;
        }

        const formData = new FormData(questionForm);
        const options = formData.getAll("option").map((value) => String(value).trim()).filter(Boolean);
        const correctOptionIndex = Number(formData.get("correct_option") || 0);

        const response = await fetch(`/api/sessions/${sessionId}/questions`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                Accept: "application/json",
            },
            body: JSON.stringify({
                prompt: formData.get("prompt"),
                options,
                correct_option_index: correctOptionIndex,
                time_limit_seconds: formData.get("time_limit_seconds"),
                points_base: formData.get("points_base"),
            }),
        });

        if (response.ok) {
            const timeLimit = formData.get("time_limit_seconds");
            const pointsBase = formData.get("points_base");
            questionForm.reset();
            questionForm.elements.time_limit_seconds.value = timeLimit;
            questionForm.elements.points_base.value = pointsBase;
            resetOptionFields();
            await refresh();
        }
    });

    panel.addEventListener("click", async (event) => {
        const toggleButton = event.target.closest("[data-toggle-question]");
        if (toggleButton) {
            await fetch(`/api/questions/${toggleButton.dataset.toggleQuestion}/toggle`, {
                method: "POST",
                headers: { Accept: "application/json" },
            });
            await refresh();
            return;
        }

        const deleteQuestionButton = event.target.closest("[data-delete-question]");
        if (deleteQuestionButton) {
            await fetch(`/api/questions/${deleteQuestionButton.dataset.deleteQuestion}`, {
                method: "DELETE",
                headers: { Accept: "application/json" },
            });
            await refresh();
            return;
        }

        const deleteSessionButton = event.target.closest("[data-delete-session]");
        if (deleteSessionButton) {
            if (!window.confirm("Delete this session and all of its questions?")) {
                return;
            }

            const response = await fetch(`/api/sessions/${deleteSessionButton.dataset.deleteSession}`, {
                method: "DELETE",
                headers: { Accept: "application/json" },
            });

            if (!response.ok) {
                window.alert("Could not delete the session. Please try again.");
                return;
            }

            await refresh();
        }
    });

    async function refresh() {
        const response = await fetch(stateUrl, {
            headers: { Accept: "application/json" },
            cache: "no-store",
        });
        const data = await response.json();
        render(data);

        if (data.sessions.length > 0) {
            const selected = data.sessions.find((item) => String(item.id) === String(sessionPicker.value)) || data.sessions[0];
            sessionPicker.value = selected.id;
            updateQrPreview(selected);
        }
    }

    refresh();
    window.setInterval(refresh, 5000);
}


function icon(name) {
    const icons = {
        "arrow-left": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 12H5"></path><path d="m12 19-7-7 7-7"></path></svg>',
        "arrow-right": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14"></path><path d="m12 5 7 7-7 7"></path></svg>',
        check: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6 9 17l-5-5"></path></svg>',
        circle: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="8"></circle></svg>',
        flag: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 22V4"></path><path d="M5 4h12l-2 5 2 5H5"></path></svg>',
        mission: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"></circle><circle cx="12" cy="12" r="4"></circle><path d="M12 3v3"></path><path d="M21 12h-3"></path><path d="M12 21v-3"></path><path d="M3 12h3"></path></svg>',
        pause: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M8 5v14"></path><path d="M16 5v14"></path></svg>',
        x: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M18 6 6 18"></path><path d="m6 6 12 12"></path></svg>',
    };
    return icons[name] || icons.circle;
}


function escapeHtml(value) {
    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#39;");
}


function escapeAttribute(value) {
    return escapeHtml(value).replaceAll("`", "&#96;");
}
