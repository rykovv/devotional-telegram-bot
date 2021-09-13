from db.base import Session

from db.devotional import Devotional
from db.book import Book
from db.study import Study

from utils.consts import MATERIAL_TYPES
from utils.utils import extract_material_name

def compose(subscription_title, month, day, cron_day):
    if MATERIAL_TYPES[subscription_title] == 'Devotional':
        message, file_ids = compose_devotional_message(subscription_title, day, month)
    elif MATERIAL_TYPES[subscription_title] == 'Book':
        message, file_ids = compose_book_message(subscription_title, cron_day+1)
    elif MATERIAL_TYPES[subscription_title] == 'Study':
        message, file_ids = compose_study_message(subscription_title, cron_day+1)
    else:
        raise Exception(f'Unknown material option: title={subscription_title}, month={month}, day={day}, cron_day={cron_day+1}')

    return message, file_ids


def compose_devotional_message(subscription_title, day, month):
    session = Session()
    devotional = session.query(Devotional).filter(Devotional.name == extract_material_name(subscription_title), Devotional.month == month, Devotional.day == day).all()
    session.close()
    try:
        devotional = devotional[0]
        # text portion composition
        message = f'\U0001F4C5<b> {devotional.date}</b>\n\U0001F4C3 <b>{devotional.title}</b>\n\n <i>\U0001F4D6 {devotional.verse}</i>\n\n'
        for paragraph in devotional.paragraphs:
            message += (paragraph + '\n\n')
        # urls tailing
        for source, url in devotional.urls.items():
            message += f'{source}: {url}\n'

        return message, devotional.telegram_file_ids
    except:
        message =   'Querido hermano/a,\n\n' \
                    'Lamentablemente, esta matutina originalmente no tiene este día. ' \
                    'Mañana Usted va a recibir el devocional del día. ' \
                    'Esto ocurre porque algunos devocionales no tienen días como el 29 de Febrero.\n\n' \
                    'Pedimos nuestras disculpas,\n' \
                    'El equipo de Una Mirada de Fe y Esperanza'

        return message, {}


def compose_book_message(subscription_title, day):
    session = Session()
    chapter = session.query(Book).filter(Book.name == extract_material_name(subscription_title), Book.chapter_number == day).all()
    session.close()
    try:
        chapter = chapter[0]
        # text portion composition
        message = f'\U0001F4D6<b> Capítulo {chapter.chapter_number}</b>\n\U0001F4C3 <b>{chapter.chapter_title}</b>\n\n'
        for paragraph in chapter.paragraphs:
            message += (paragraph + '\n\n')
        # video url tailing
        for source, url in chapter.urls.items():
            message += f'{source}: {url}'
        
        return message, chapter.telegram_file_ids
    except:
        message =   'Querido hermano/a,\n\n' \
                    'Lamentablemente, esta lectura ha llegado a su fin. ' \
                    'Usted ya ha recibido todos los capítulos y no hay nada más que enviar.\n\n' \
                    'Esperamos mucho que haya sido de bendición espíritual.\n' \
                    '¡Felicidades por terminar la lectura!\n' \
                    'El equipo de Una Mirada de Fe y Esperanza'

        return message, {}

def compose_study_message(subscription_title, day):
    session = Session()
    study = session.query(Study).filter(Study.book_name == extract_material_name(subscription_title), Study.day == day).all()
    session.close()
    try:
        study = study[0]
        # text portion composition
        message =   f'\U0001F4C5 <b>Día {study.day}</b>\n\U0001F4C3 <b>{study.chapter_title}, párrafos {study.chapter_paragraphs}</b>\n\n' \
                    f'<i>\U0001F4D6 {study.verse}</i>\n\n'
        for paragraph in study.paragraphs:
            message += (paragraph + '\n\n')
        # urls tailing
        for source, url in study.urls.items():
            message += f'{source}: {url}\n'

        return message, study.telegram_file_ids
    except:
        message =   'Querido hermano/a,\n\n' \
                    'Usted ya ha recibido todos los días de este estudio y no hay nada más que enviar.\n\n' \
                    'Esperamos mucho que haya sido de bendición espíritual para Usted.\n' \
                    '¡Felicidades por terminar el estudio!\n' \
                    'El equipo de Una Mirada de Fe y Esperanza'

        return message, {}