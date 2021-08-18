import random as rand

from sqlalchemy.sql.base import prefix_anon_map
from sqlalchemy.sql.functions import random
from db.base import Session
from db.subscription import Subscription
from db.quiz import Quiz
from db.question import Question
from db.subscription import Subscription
from db.study import Study

from actors import composer

from utils import buffer
from utils.utils import (
    days_since_epoch, 
    extract_material_name,
    make_inclusive_range
)
from utils.types import TelegramKeyboard
from utils.helpers import (
    fetch_question, 
    average_study_knowledge,
    chapter_questions_count,
    most_recent_quiz
)
import utils.consts as consts
from utils.decorators import with_session

def start_quiz(subscriber_id: int, subscription: Subscription):
    subscription_day = days_since_epoch(subscription.creation_utc)+1
    
    session = Session()
    study = session \
        .query(Study) \
        .filter( \
            Study.book_name == extract_material_name(subscription.devotional_name), 
            Study.day == days_since_epoch(subscription.creation_utc)+1) \
        .all()[0]
    days_in_chapter = session \
        .query(Study) \
        .filter(
            Study.book_name == extract_material_name(subscription.devotional_name), 
            Study.chapter_number==study.chapter_number) \
        .count()
    session.close()
    mrq = most_recent_quiz(subscription)

    # TODO: Chapter quiz MUST BE TESTED
    chaper_quiz = mrq != None and days_in_chapter == mrq.day
    if chaper_quiz:
        total_questions = min(consts.CHAPTER_QUIZ_TOTAL_QUESTIONS, chapter_questions_count(study))
        questions_range = rand.sample(range(1, chapter_questions_count(study)+1), total_questions)
    else:
        total_questions = min(consts.DAY_QUIZ_TOTAL_QUESTIONS, len(make_inclusive_range(study.questions)))
        questions_range = rand.sample(make_inclusive_range(study.questions), total_questions)

    buffer.add_quiz(
        subscriber_id, 
        Quiz(
            subscription_id=subscription.id, 
            book_name=extract_material_name(subscription.devotional_name), 
            study_name='El Tiempo de Estar Preparado',
            day=subscription_day,
            questions=study.questions,
            questions_range=questions_range,
            chapter=study.chapter_number,
            total=total_questions,
            chapter_quiz=chaper_quiz,
            completion_utc=None
        )
    )

    question_str, telegram_keyboard = next_question(subscriber_id)
    if not chaper_quiz:
        preface =   f'📝 Cuestionario del día {subscription_day}\n'
    else:
        preface =   f'📝 Cuestionario del capíluto {study.chapter_number}\n'
                    
    preface +=  f'🏁 ¡Empecemos! 🏁\n\n' \
                f'{question_str}'

    return preface, telegram_keyboard

def next_question(subscriber_id: int, prev_response: str = None):
    question_str = ''

    questions_range = buffer.quizzes[subscriber_id].questions_range
    question_str += _process_question(prev_response, subscriber_id, questions_range, buffer.quizzes[subscriber_id].current_question)

    if not quiz_finished(subscriber_id):
        question = fetch_question(subscriber_id, questions_range, buffer.quizzes[subscriber_id].current_question)

        question_str += f'Pregunta {buffer.quizzes[subscriber_id].current_question+1} de {buffer.quizzes[subscriber_id].total}\n\n' \
                        f'💭 {question.question} 💭\n\n' \
                        f'{question.make_str_options()}'
        buffer.quizzes[subscriber_id].current_question += 1
        return question_str, question.make_telegram_keyboard()
    else:
        return None

# returns a bool value indicating if current
#   quiz is done
def quiz_finished(subscriber_id: int) -> bool:
    return subscriber_id in buffer.quizzes and buffer.quizzes[subscriber_id].finished()

# returns a tuple of str (1) current quiz report when
#   it is done, and (2) if this is the last quiz
#   of the chapter and the chapter quiz can be started
#   next
def quiz_report(subscriber_id: int, last_respone: str):
    report = _process_question(last_respone, subscriber_id, buffer.quizzes[subscriber_id].questions_range, buffer.quizzes[subscriber_id].current_question)

    session = Session()
    buffer.quizzes[subscriber_id].make_knowledge()
    session.add(buffer.quizzes[subscriber_id])
    session.commit()

    if not buffer.quizzes[subscriber_id].chapter_quiz:
        report +=    f'🙌 El cuestionario del día {buffer.quizzes[subscriber_id].day} completado con éxito 🙌\n\n'
    else:
        report +=    f'🙌 El cuestionario general del capítulo {buffer.quizzes[subscriber_id].chapter} completado con éxito 🙌\n\n'

    report +=   '🎌 Informe 🎌\n' \
                f'✅ Respuestas correctas: {buffer.quizzes[subscriber_id].correct} de {buffer.quizzes[subscriber_id].total}\n' \
                f'💯 Calificación: {int(buffer.quizzes[subscriber_id].knowledge)} de 100\n' \
                f'📈 Conocimiento medio del libro: {int(average_study_knowledge(subscriber_id))} de 100.'
    
    days_in_chapter = session \
        .query(Study) \
        .filter(
            Study.book_name == buffer.quizzes[subscriber_id].book_name, 
            Study.chapter_number == buffer.quizzes[subscriber_id].chapter) \
        .count()
    session.close()
    mrq = most_recent_quiz(buffer.subscriptions[subscriber_id])

    last_quiz = mrq != None and days_in_chapter == mrq.day
    if last_quiz and not buffer.quizzes[subscriber_id].chapter_quiz:
        report +=   f'\n\nÉste fue el último cuestionario del capítulo {buffer.quizzes[subscriber_id].chapter}. ' \
                    'Ahora Usted está listo/a para empezar el cuestionario ' \
                    'del capítulo entero. ¡Marque 👉 /cuestionario 👈 para empezar!'
    else:
        report +=   '\n\nSi quiere repetir la prueba con más preguntas marque 👉 /cuestionario 👈 de nuevo.'
    
    buffer.delete_quiz(subscriber_id)

    return report, last_quiz

def quiz_started(subscriber_id : int):
    return subscriber_id in buffer.quizzes


def _process_question(prev_response: str, subscriber_id: int, questions_range: list[int], current_question: int):
    question_str = ''
    if not prev_response in [None, '']:
        prev_question = fetch_question(subscriber_id, questions_range, current_question-1)
        if prev_question.test_response(prev_response):
            question_str += '✅ Correcto\n\n'
            buffer.quizzes[subscriber_id].add_correct()
        else:
            question_str += '❌ Incorrecto\n\n'
            buffer.quizzes[subscriber_id].add_wrong()
        question_str += f'\U0001F4D6 {prev_question.reference}\n\n'
    return question_str