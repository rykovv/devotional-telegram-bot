from utils.utils import days_since_epoch, extract_material_name
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

from utils.decorators import make_session_scope


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
        delete_subscription(subscription.id)
        delete_subscriber(subscriber.id)
        actuary.add_unsubscribed()

        return 'Subscriber and subscription were deleted.'
    return 'No action taken at exception.'


def subscriptions_count(sid) -> int:
    session = Session()
    count = session.query(Subscription).filter(Subscription.subscriber_id == sid).count()
    session.close()
    return count


def persist_buffer(userid) -> None:
    with make_session_scope() as session:
        if userid in buffer.subscribers:
            buffer.subscribers[userid].persist(session)
            actuary.set_last_registered(epoch=buffer.subscribers[userid].creation_utc)
        if userid in buffer.subscriptions:
            buffer.subscriptions[userid].persist(session)
            actuary.set_last_subscribed(epoch=buffer.subscriptions[userid].creation_utc)


def clean_db(userid) -> None:
    if userid in buffer.subscriptions:
        delete_subscription( buffer.subscriptions[userid].id )
    if userid in buffer.subscribers:
        delete_subscriber(userid)

# this function may be useful when a fast sudden subscriber deletion may take place
#   and sqlalchemy lazy loading would not have enough time to load all relationships  
def delete_subscriber(subscriber_id: int):
    with Session() as session:
        subscriber = session.query(Subscriber).get(subscriber_id)
        session.delete(subscriber)
        session.commit()

def delete_subscription(subscription_id: int):
    with Session() as session:
        subscription = session.query(Subscription).get(subscription_id)
        session.delete(subscription)
        session.commit()

def print_subscription(subscription: Subscription, skipped: Boolean = False) -> str:
    material_type = consts.MATERIAL_TYPES[subscription.title]
    if material_type == 'Devotional':
        item = 'devocional'
    elif material_type == 'Book':
        item = 'capítulo'
    elif material_type == 'Study':
        item = 'estudio'
    elif material_type == 'Promise':
        item = 'promesa'
    if skipped:
        return f'{subscription.title}, 1 {item} cada día a la(s) {subscription.preferred_time_local} PST del día anterior.'
    else:
        return f'{subscription.title}, 1 {item} cada día a la(s) {subscription.preferred_time_local}.'


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

def prepare_studies_reply(studies: Subscription):
    studies_str = ''
    studies_kb = []
    for i, study in enumerate(studies):
        studies_str += f'{i+1}. {extract_material_name(study.title)}, día {days_since_epoch(study.creation_utc)+1}\n'
        if i % consts.SUBSCRIPTIONS_BY_ROW == 0:
            studies_kb.append([str(i+1)])
        else:
            studies_kb[i//consts.SUBSCRIPTIONS_BY_ROW].append(str(i+1))

    return studies_str, studies_kb


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


def chapter_questions_count(study: Study, chapter_number: int = None) -> int:
    session = Session()
    count = session.query(Question) \
        .filter(
            Question.book_name == study.book_name, 
            Question.chapter_number == (study.chapter_number if chapter_number == None else chapter_number)) \
        .count()
    session.close()
    return count

def study_days_in_chapter(subscription: Subscription) -> int:
    session = Session()
    study = session \
        .query(Study) \
        .filter( \
            Study.book_name == extract_material_name(subscription.title), 
            Study.day == days_since_epoch(subscription.creation_utc)+1) \
        .all()[0]
    days_in_chapter = session \
        .query(Study) \
        .filter(
            Study.book_name == extract_material_name(subscription.title), 
            Study.chapter_number==study.chapter_number) \
        .count()
    session.close()

    return days_in_chapter


def most_recent_quiz(subscription: Subscription) -> Quiz:
    session = Session()
    mrq = session \
        .query(Quiz) \
        .filter(
            Quiz.subscription_id == subscription.id) \
        .order_by(
            Quiz.completion_utc.desc()) \
        .limit(1) \
        .all()
    session.close()
    return mrq[0] if len(mrq) == 1 else None


def chapter_quiz_ready(subscription: Subscription) -> bool:
    # last day quiz of the chapter can be deduced
    days_in_chapter = study_days_in_chapter(subscription)
    mrq = most_recent_quiz(subscription)
    return False if mrq == None else mrq.day == days_in_chapter


def persisted_subscription(subscription: Subscription) -> bool:
    session = Session()
    ret = session.query(Subscription).filter(Subscription.id == subscription.id).all()
    session.close()
    return len(ret) == 1

def get_study_subscription_by_acronym(study_subscriptions: list[Subscription], acronym: str) -> Subscription:
    study = filter(lambda s: s.title == f'Estudio: {consts.BOOKS_ACRONYMS_LUT[acronym.upper()]}', study_subscriptions)
    study = list(study)
    return study[0] if len(study) == 1 else None