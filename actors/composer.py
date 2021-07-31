from db.devotional import Devotional
from db.base import Session


def compose(name, month, day, cron_day):
    message = ''
    audio_id = []
    if name == '¡Maranata: El Señor Viene!':
        message, audio_id = compose_devotional_message(name, day, month)
    elif name == 'El Conflicto de los Siglos':
        message, audio_id = compose_book_message(name, str(cron_day+1))
    else:
        raise Exception(f'Unknown devotional option: name={name}, month={month}, day={day}, cron_day={cron_day}')

    return (message, audio_id)


def compose_devotional_message(name, day, month):
    session = Session()
    devotional = session.query(Devotional).filter(Devotional.name == name, Devotional.month == str(month), Devotional.day == str(day)).all()
    session.close()
    audio_id = []
    if devotional != []:
        devotional = devotional[0]
        # text portion composition
        message = f'\U0001F4C5<b> {devotional.date}</b>\n\U0001F4C3 <b>{devotional.title}</b>\n\n <i>\U0001F4D6 {devotional.verse}</i>\n\n'
        for k, v in devotional.paragraphs.items():
            message += (v + '\n\n')
        # video url tailing
        message += f'{devotional.url}'
        # telegram file_id capturing
        if devotional.audio_file_ids != None:
            audio_id = devotional.audio_file_ids
    else:
        message =   'Querido hermano/a,\n\n' \
                    'Lamentablemente, esta matutina originalmente no tiene este día. ' \
                    'Mañana Usted va a recibir el devocional del día. ' \
                    'Esto ocurre porque algunos devocionales no tienen días como el 29 de Febrero.\n\n' \
                    'Pedimos nuestras disculpas,\n' \
                    'El equipo de Una Mirada de Fe y Esperanza'

    return (message, audio_id)


def compose_book_message(name, day):
    session = Session()
    devotional = session.query(Devotional).filter(Devotional.name == name, Devotional.day == str(day)).all()
    session.close()
    audio_id = []
    if devotional != []:
        devotional = devotional[0]
        # text portion composition
        message = f'\U0001F4D6<b> {devotional.verse}</b>\n\U0001F4C3 <b>{devotional.title}</b>\n\n'
        for k, v in devotional.paragraphs.items():
            message += (v + '\n\n')
        # video url tailing
        message += f'{devotional.url}'
        # telegram file_id capturing
        if devotional.audio_file_ids != None:
            audio_id = devotional.audio_file_ids
    else:
        message =   'Querido hermano/a,\n\n' \
                    'Lamentablemente, esta lectura ha llegado a su fin. ' \
                    'Usted ya ha recibido todos los capítulos y no hay nada más que enviar.\n\n' \
                    'Esperamos mucho que haya sido de bendición espíritual.\n' \
                    'Que el Señor le bendiga,\n' \
                    'El equipo de Una Mirada de Fe y Esperanza'

    return (message, audio_id)