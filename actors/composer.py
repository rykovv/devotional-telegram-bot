from db.devotional import Devotional
from db.base import Session

def compose(name, month, day):
    session = Session()
    devotional = session.query(Devotional).filter(Devotional.name == name, Devotional.month == str(month), Devotional.day == str(day)).all()[0]
    message = f'\U0001F4C5<b> {devotional.date}</b>\n\U0001F4C3 <b>{devotional.title}</b>\n\n <i>\U0001F4D6 {devotional.verse}</i>\n\n'
    for k, v in devotional.paragraphs.items():
        message += (v + '\n\n')
    message += f'{devotional.url}'

    return (message, devotional.title_date, devotional.audio_file_id)