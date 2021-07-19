from configparser import ConfigParser

import telegram
from db.base import Session

import utils.consts as consts
from utils.utils import (
    get_current_utc_hour,
    get_send_month_day,
    get_logger,
)

from db.subscription import Subscription

import actors.composer as composer
import actors.actuary as actuary

config = ConfigParser()
config.read(consts.CONFIG_FILE_NAME)

logger = get_logger()


def send(all=False, month=None, day=None):
    session = Session()
    if not all:
        current_hour = consts.TF_24TO12[get_current_utc_hour()]
        subscriptions = session.query(Subscription).filter(Subscription.preferred_time_utc.ilike(f'{current_hour}%')).all()
    else:
        subscriptions = session.query(Subscription).all()
    session.close()

    bot = telegram.Bot(token=config['bot']['token'])
    
    sent = 0
    retries = 0
    # must assure max sending of 30 messages per second, that's 33.33ms per message
    for subscription in subscriptions:
        done = False
        while not done:
            try:
                if month == None and day == None:
                    date = get_send_month_day(subscription.preferred_time_utc)
                else:
                    date = {'month':month, 'day':day}
                    
                # compose a formatted message
                msg, title, file_id = composer.compose(subscription.devotional_name, date['month'], date['day'])

                # send files if available
                if file_id != None:
                    bot.send_document(chat_id=str(subscription.subscriber_id), document=file_id)
                # send text next to the files
                bot.send_message(chat_id=str(subscription.subscriber_id), text=msg, parse_mode='html')
                
                sent += 1
                done = True
            except Exception as e:
                report_exception(f'{e} sending at {date} to {str(subscription.subscriber_id)}')
                retries += 1

    if sent > 0:
        actuary.add_sent(sent)

    if not all:
        logger.info(f'Devotionals sent at {consts.TF_24TO12[get_current_utc_hour()]} with {retries} retries.')
    else:
        logger.info(f'Devotionals have been sent to all users at {consts.TF_24TO12[get_current_utc_hour()]} with {retries} retries.')


def send_global_message(msg):
    session = Session()
    subscriptions = session.query(Subscription).all()
    session.close()

    bot = telegram.Bot(token=config['bot']['token'])
    
    sent = 0
    retries = 0
    # must assure max sending of 30 messages per second, that's 33.33ms per message
    for subscription in subscriptions:
        done = False
        while not done:
            try:
                bot.send_message(chat_id=str(subscription.subscriber_id), text=msg, parse_mode='html')
                sent += 1
                done = True
            except Exception as e:
                report_exception(f'{e} sending at {get_current_utc_hour()} to {str(subscription.subscriber_id)}')
                retries += 1

    if sent > 0:
        actuary.add_sent(sent)

    logger.warn(f'Global message has been sent to all users at {consts.TF_24TO12[get_current_utc_hour()]} '
    'with {retries} retries.\n\nMessage content: {msg}.')


def report_exception(exception):
    bot = telegram.Bot(token=config['bot']['token'])
    bot.send_message(chat_id=config['admin']['chat_id'], text=str(exception), parse_mode='html')
    