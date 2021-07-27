from db.devotional import Devotional
from db.base import Session

def compose(name, month, day):
    session = Session()
    devotional = session.query(Devotional).filter(Devotional.name == name, Devotional.month == str(month), Devotional.day == str(day)).all()
    session.close()
    audio_id = ''
    if devotional != []:
        devotional = devotional[0]
        message = f'\U0001F4C5<b> {devotional.date}</b>\n\U0001F4C3 <b>{devotional.title}</b>\n\n <i>\U0001F4D6 {devotional.verse}</i>\n\n'
        for k, v in devotional.paragraphs.items():
            message += (v + '\n\n')
        message += f'{devotional.url}'
        audio_id = devotional.audio_file_ids
    else:
        message =   'Querido hermano/hermana,\n\n' \
                    'Lamentablemente, esta matutina originalmente no tiene este día. ' \
                    'Mañana Usted va a recibir el devocional del día. ' \
                    'Esto ocurre porque algunos devocionales no tienen días como el 29 de Febrero.\n\n' \
                    'Pedimos nuestras disculpas,\n' \
                    'El equipo de Una Mirada de Fe y Esperanza'

    return (message, audio_id)