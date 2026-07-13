from os import getenv

from models import db, Users, Polls, Topics, Options, UserPolls
from flask import Blueprint, request, jsonify, session
from datetime import datetime
from config import SQLALCHEMY_DATABASE_URI

if getenv('APP_MODE') == 'PRODUCTION':
    from production_settings import SQLALCHEMY_DATABASE_URI


api = Blueprint('api', 'api', url_prefix='/api')


@api.route('/polls', methods=['GET', 'POST'])
# retrieves/adds polls from/to the database
def api_polls():
    if request.method == 'POST':
        if session.get('user') != 'Administrator':
            return jsonify({'message': 'Only the Administrator can create polls'}), 403

        # get the poll and save it in the database
        poll = request.get_json()

        # simple validation to check if all values are properly set
        for key, value in poll.items():
            if not value:
                return jsonify({'message': 'value for {} is empty'.format(key)})

        title = poll['title']
        options_query = lambda option: Options.query.filter(Options.name.like(option))

        options = [Polls(option=Options(name=option))
                   if options_query(option).count() == 0
                   else Polls(option=options_query(option).first()) for option in poll['options']
                   ]
        eta = datetime.utcfromtimestamp(poll['close_date'])
        new_topic = Topics(title=title, options=options, close_date=eta)

        db.session.add(new_topic)
        db.session.commit()

        # run the task (opcional: requer um broker Celery, ex. RabbitMQ)
        try:
            from tasks import close_poll
            close_poll.apply_async((new_topic.id, SQLALCHEMY_DATABASE_URI), eta=eta)
        except Exception as exc:
            print(f'[warn] Celery indisponivel, poll nao sera fechado automaticamente: {exc}')

        return jsonify({
            'message': 'Poll was created succesfully',
            'poll_id': new_topic.id,
        })

    else:
        # it's a GET request, return dict representations of the API
        polls = Topics.query.filter_by(status=True).join(Polls).order_by(Topics.id.desc()).all()
        all_polls = {'Polls':  [poll.to_json() for poll in polls]}

        return jsonify(all_polls)


@api.route('/polls/options')
def api_polls_options():

    all_options = [option.to_json() for option in Options.query.all()]

    return jsonify(all_options)


@api.route('/poll/vote', methods=['PATCH'])
def api_poll_vote():
    poll = request.get_json(silent=True) or {}
    option = poll.get('option')
    topic_id = poll.get('topic_id')
    poll_title = poll.get('poll_title')

    if not option or (not topic_id and not poll_title):
        return jsonify({'message': 'A poll and option are required'}), 400

    join_tables = Polls.query.join(Topics).join(Options)

    # Get topic and username from the database
    if topic_id:
        topic = db.session.get(Topics, topic_id)
        if topic and not topic.status:
            topic = None
    else:
        topic = Topics.query.filter_by(title=poll_title, status=True).first()

    user = Users.query.filter_by(username=session['user']).first() if session.get('user') else None

    # if poll was closed in the background before user voted
    if not topic:
        return jsonify({'message': 'Sorry! this poll has been closed'})

    # filter options
    option_query = join_tables.filter(Topics.status == True).filter(Options.name.like(option))
    if topic:
        option_query = option_query.filter(Topics.id == topic.id)
    else:
        option_query = option_query.filter(Topics.title.like(poll_title))
    option = option_query.first()

    # check if the user has voted on this poll
    if user:
        poll_count = UserPolls.query.filter_by(topic_id=topic.id).filter_by(user_id=user.id).count()
        if poll_count > 0:
            return jsonify({'message': 'Sorry! multiple votes are not allowed'})
    else:
        anonymous_votes = session.get('anonymous_votes', [])
        if topic.id in anonymous_votes:
            return jsonify({'message': 'Sorry! multiple votes are not allowed'})

    if option:
        # record user and poll
        if user:
            user_poll = UserPolls(topic_id=topic.id, user_id=user.id)
            db.session.add(user_poll)
        else:
            anonymous_votes = session.get('anonymous_votes', [])
            anonymous_votes.append(topic.id)
            session['anonymous_votes'] = anonymous_votes

        # increment vote_count by 1 if the option was found
        option.vote_count += 1
        db.session.commit()

        return jsonify({'message': 'Thank you for voting'})

    return jsonify({'message': 'option or poll was not found please try again'})


@api.route('/poll/<poll_name>')
def api_poll(poll_name):

    poll = Topics.query.filter(Topics.title.like(poll_name)).first()

    return jsonify({'Polls': [poll.to_json()]}) if poll else jsonify({'message': 'poll not found'})
