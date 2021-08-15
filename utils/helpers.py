from db.question import Question
from sqlalchemy.sql.sqltypes import Boolean
from sqlalchemy.sql import func
from db.base import Session
from db.subscription import Subscription
from db.subscriber import Subscriber
from db.study import Study
from db.quiz import Quiz
from db.question import Question
import actors.actuary as actuary

import utils.buffer as buffer
import utils.consts as consts
from utils.utils import extract_material_name


def fetch_subscriber(id) -> Subscriber:
    session = Session()
    subscriber = session.query(Subscriber).get(id)
    session.close()

    return subscriber

def fetch_question(subscriber_id, questions_range, question_range_index) -> Question:
    session = Session()
    question = session \
        .query(Question) \
        .filter(
            Question.book_name == buffer.quizzes[subscriber_id].book_name,
            Question.chapter_number == buffer.quizzes[subscriber_id].chapter,
            Question.number == questions_range[question_range_index]) \
        .all()[0]
    session.close()
    return question

def process_send_exception(exception, subscription) -> str:
    if str(exception) == 'Forbidden: bot was blocked by the user':
        session = Session()
        subscriber = session.query(Subscriber).get(subscription.subscriber_id)
        session.close()
        subscription.delete()
        subscriber.delete()
        actuary.add_unsubscribed()

        return 'Subscriber and subscription were deleted.'
    return 'No action taken at exception.'


def subscriptions_count(sid) -> int:
    session = Session()
    count = session.query(Subscription).filter(Subscription.subscriber_id == sid).count()
    session.close()
    return count


def persist_buffer(userid) -> None:
    if userid in buffer.subscribers:
        buffer.subscribers[userid].persist()
        actuary.set_last_registered()
    if userid in buffer.subscriptions:
        buffer.subscriptions[userid].persist()
        actuary.set_last_subscribed()


def clean_db(userid) -> None:
    if userid in buffer.subscriptions:
        buffer.subscriptions[userid].delete()
    if userid in buffer.subscribers:
        buffer.subscribers[userid].delete()


def print_subscription(subscription: Subscription, skipped: Boolean = False) -> str:
    if skipped:
        return f'{subscription.devotional_name} cada día a la(s) {subscription.preferred_time_local} PST del día anterior.'
    else:
        return f'{subscription.devotional_name} cada día a la(s) {subscription.preferred_time_local}.'


def prepare_subscriptions_reply(subscriptions, str_only=False, kb_only=False, skipped=False):
    subscriptions_str = ''
    subscriptions_kb = []
    for i, subscription in enumerate(subscriptions):
        subscriptions_str += f'{i+1}. {print_subscription(subscription, skipped)}\n'
        if i % consts.SUBSCRIPTIONS_BY_ROW == 0:
            subscriptions_kb.append([str(i+1)])
        else:
            subscriptions_kb[i//consts.SUBSCRIPTIONS_BY_ROW].append(str(i+1))

    return (subscriptions_str if str_only else (subscriptions_kb if kb_only else subscriptions_str, subscriptions_kb))

def average_study_knowledge(subscriber_id: int):
    session = Session()
    average_by_day = session \
        .query(func.avg(Quiz.knowledge)) \
        .filter(
            Quiz.subscription_id == buffer.quizzes[subscriber_id].subscription_id).scalar()
    # average_by_chapter = session \
    #     .query(func.avg(Quiz.knowledge)) \
    #     .filter(
    #         Quiz.subscription_id == buffer.quizzes[subscriber_id].subscription_id, 
    #         Quiz.chapter_quiz == True).scalar()
    session.close()
    # print(average_by_chapter, average_by_day, type(average_by_day))

    # if average_by_chapter == None:
    #     print(f'by_day : {average_by_day}, by_chapter : {average_by_chapter}, total : {average_by_day*consts.QUIZ_DAY_PONDERATION}')
    #     return average_by_day
    # else:
    #     print(f'by_day : {average_by_day}, by_chapter : {average_by_chapter}, total : {average_by_day*consts.QUIZ_DAY_PONDERATION + average_by_chapter*consts.QUIZ_CHAPTER_PONDERATION}')
    #     return (average_by_day*consts.QUIZ_DAY_PONDERATION + average_by_chapter*consts.QUIZ_CHAPTER_PONDERATION)
    return average_by_day


def chapter_questions_count(study: Study) -> int:
    session = Session()
    count = session.query(Question).filter(Question.book_name == study.book_name, Question.chapter_number == study.chapter_number).count()
    session.close()
    return count