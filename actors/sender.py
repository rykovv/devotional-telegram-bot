from configparser import ConfigParser

import telegram
from db.base import Session
from utils.utils import get_current_utc_hour, get_send_month_day
import utils.consts as consts

from db.subscription import Subscription

import actors.composer as composer
import actors.actuary as actuary

config = ConfigParser()
config.read(consts.CONFIG_FILE_NAME)

def send():
    session = Session()
    current_hour = consts.TF_24TO12[get_current_utc_hour()]
    subscriptions = session.query(Subscription).filter(Subscription.preferred_time_utc.ilike(f'{current_hour}%')).all()

    bot = telegram.Bot(token=config['bot']['token'])
    
    sent = 0
    for subscription in subscriptions:
        try:
            date = get_send_month_day(subscription.preferred_time_utc)
            msg, title, file_id = composer.compose(subscription.devotional_name, date['month'], date['day'])
            if file_id != None:
                bot.send_document(chat_id=str(subscription.subscriber_id), document=file_id)
            bot.send_message(chat_id=str(subscription.subscriber_id), text=msg, parse_mode='html')
            sent += 1
        except Exception as e:
            report_exception(f'{e} sending at {date} to {str(subscription.subscriber_id)}')
    
    if sent > 0:
        actuary.add_sent(sent)

    print(f'devotionals sent at {consts.TF_24TO12[get_current_utc_hour()]}')

def report_exception(exception):
    bot = telegram.Bot(token=config['bot']['token'])
    bot.send_message(chat_id=config['admin']['chat_id'], text=str(exception), parse_mode='html')
    