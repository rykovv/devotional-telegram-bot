from db.devotional import Devotional
from db.base import Session


def compose(name, month, day, cron_day):
    if name == '¡Maranata: El Señor Viene!':
        message, audio_id = compose_devotional_message(name, month, day)
    elif name == 'El Conflicto de los Siglos':
        message, audio_id = compose_book_message(name, str(cron_day+1))
    
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
        message = f'\U0001F4C5<b> {devotional.verse}</b>\n\U0001F4C3 <b>{devotional.title}</b>\n\n'
        for k, v in devotional.paragraphs.items():
            message += (v + '\n\n')
        # video url tailing
        message += f'{devotional.url}'
        # telegram file_id capturing
        if devotional.audio_file_ids != None:
            audio_id = devotional.audio_file_ids

    return (message, audio_id)