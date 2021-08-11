from sqlalchemy.sql.base import prefix_anon_map
from sqlalchemy.sql.functions import random
from db.base import Session
from db.subscription import Subscription
from db.quiz import Quiz
from db.question import Question
from db.subscription import Subscription
from db.devotional import Devotional

from actors import composer

from utils import buffer
from utils.utils import days_since_epoch

def start_quiz(subscriber_id: int, subscription: Subscription) -> str:
    subscription_day = days_since_epoch(subscription.creation_utc)
    
    session = Session()
    devotional = session \
        .query(Devotional) \
        .filter( \
            Devotional.name == subscription.devotional_name, 
            Devotional.day == str(days_since_epoch(subscription.creation_utc))) \
        .all()[0]
    chapter = devotional.verse.split(' ')[1]
    days_in_chapter = session \
        .query(Devotional) \
        .filter(
            Devotional.name == subscription.devotional_name, 
            Devotional.verse==f'Capítulo {chapter}') \
        .count()
    inchapter_quizzes = session.query(Quiz).filter(Quiz.chapter == chapter).count()
    session.close()

    questions_range = devotional.optional
    # if days_in_chapter == inchapter_quizzes:
    #    questions_range = random list of 10 questions between the first and the last question of the chapter

    buffer.add_quiz(
        subscriber_id, 
        Quiz(
            subscription_id=subscription.id, 
            book_name=subscription.devotional_name, 
            study_name='El Tiempo de Estar Preparado',
            day=subscription_day,
            questions_range=questions_range,
            chapter=chapter,
            total=len(devotional.questions_range()),
            chapter_quiz=(days_in_chapter == inchapter_quizzes)
        )
    )

    preface =   'Querído hermano/a, º\n\n' \
                f'Usted empieza el cuestionario asociado al día {subscription_day}. ' \
                f'Está compuesto de {len(devotional.questions_range())} preguntas. ' \
                f'¡Empecemos!\n\n' \
                f'{next_question(subscriber_id)}'

    return preface

def next_question(subscriber_id: int, prev_response: str) -> tuple(str, list[list[str]]):
    question_str = ''
    
    questions_range = buffer.quizzes[subscriber_id].get_questions_range()
    session = Session()
    question = session \
        .query(Question) \
        .filter(
            Question.book_name == buffer.quizzes[subscriber_id].book_name,
            Question.chapter == buffer.quizzes[subscriber_id].chapter,
            Question.number == str(questions_range[buffer.quizzes[subscriber_id].current_question])) \
        .all()[0]
    session.close()

    if not prev_response in [None, '']:
        if question.test_response(prev_response):
            question_str += '✅Correcto\n\n'
            buffer.quizzes[subscriber_id].add_correct()
        else:
            question_str += '❌Incorrecto\n\n'
            buffer.quizzes[subscriber_id].add_wrong()
        question_str += f'{question.reference}\n\n'

    if not finished(subscriber_id):
        question_str += f'Pregunta {buffer.quizzes[subscriber_id].current_question+1} de {buffer.quizzes[subscriber_id].total}\n\n' \
                        f'{question.question}\n\n' \
                        f'{question.make_str_options()}'
        return question_str, question.make_telegram_keyboard()
    else:
        buffer.quizzes[subscriber_id].make_knowledge()
        buffer.quizzes[subscriber_id].persist()
        return None

# returns a bool value indicating if current
#   quiz is done
def finished(subscriber_id: int) -> bool:
    return buffer.quizzes[subscriber_id].finished()

# returns a tuple of str (1) current quiz report when
#   it is done, and (2) if this is the last quiz
#   of the chapter and the chapter quiz can be started
#   next
def quiz_report(subscriber_id: int) -> tuple(str, bool):
    report =    'El cuestionario completado con éxito.\n\n' \
                f'Usted ha contestado bien a {buffer.quizzes[subscriber_id].correct} ' \
                f'preguntas de {buffer.quizzes[subscriber_id].total} ' \
                f'teniendo el conocimiento medio de la lectura {int(buffer.quizzes[subscriber_id].knowledge*100)}/100.'
    
    session = Session()
    days_in_chapter = session \
        .query(Devotional) \
        .filter(
            Devotional.name == buffer.quizzes[subscriber_id].book_name, 
            Devotional.verse == f'Capítulo {buffer.quizzes[subscriber_id].chapter}') \
        .count()
    inchapter_quizzes = session.query(Quiz).filter(Quiz.chapter == buffer.quizzes[subscriber_id].chapter).count()
    session.close()

    last_quiz = days_in_chapter==inchapter_quizzes
    if last_quiz:
        report +=   'Éste fue el último cuestionario del capítulo. ' \
                    'Ahora Usted está listo/a para empezar el cuestionario ' \
                    'del capítulo. ¡Marque /cuestionario para empezar!'

    buffer.delete_quiz(subscriber_id)

    return report, last_quiz