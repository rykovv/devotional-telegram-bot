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

import time
import datetime as dt

config = ConfigParser()
config.read(consts.CONFIG_FILE_NAME)

logger = get_logger()
_last_send_timestamp = dt.datetime.utcnow()

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
                msg, file_ids = composer.compose(subscription.devotional_name, date['month'], date['day'])

                # send files if available
                _send_document(bot, subscription.subscriber_id, file_ids, consts.LEAST_BOT_SEND_MS)

                # send text next to the files
                _send_message(bot, subscription.subscriber_id, msg, consts.LEAST_BOT_SEND_MS)
                
                sent += 1
                done = True
            except Exception as e:
                report_exception(f'{e} sending at {date} to {str(subscription.subscriber_id)}')
                time.sleep(pow(2, retries) if retries < 9 else consts.MAX_RESEND_DELAY)
                retries += 1
                done = retries > consts.MAX_SEND_RETRIES

    if sent > 0:
        actuary.add_sent(sent)

    if retries > consts.MAX_SEND_RETRIES:
        if not all:
            report_exception(f'Devotionals NOT sent at {consts.TF_24TO12[get_current_utc_hour()]} with {retries} retries.')
            logger.error(f'Devotionals NOT sent at {consts.TF_24TO12[get_current_utc_hour()]} with {retries} retries.')
        else:
            logger.error(f'Devotionals have NOT been sent to all users at {consts.TF_24TO12[get_current_utc_hour()]} with {retries} retries.')
    else:
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
                _send_message(bot, subscription.subscriber_id, msg, consts.LEAST_BOT_SEND_MS)
                sent += 1
                done = True
            except Exception as e:
                report_exception(f'{e} sending at {get_current_utc_hour()} to {str(subscription.subscriber_id)}')
                time.sleep(pow(2, retries) if retries < 9 else consts.MAX_RESEND_DELAY)
                retries += 1
                done = retries > consts.MAX_SEND_RETRIES

    if sent > 0:
        actuary.add_sent(sent)

    if retries > consts.MAX_SEND_RETRIES:
        report_exception(f'Global message has NOT been sent to all users at {consts.TF_24TO12[get_current_utc_hour()]} '
                         f'with {retries} retries.\n\nMessage content: {msg}.')
        logger.error(f'Global message has NOT been sent to all users at {consts.TF_24TO12[get_current_utc_hour()]} '
                    f'with {retries} retries.\n\nMessage content: {msg}.')
    else:
        logger.warn(f'Global message has been sent to all users at {consts.TF_24TO12[get_current_utc_hour()]} '
                    f'with {retries} retries.\n\nMessage content: {msg}.')


def report_exception(exception):
    bot = telegram.Bot(token=config['bot']['token'])
    _send_message(bot, config['admin']['chat_id'], str(exception), consts.LEAST_BOT_SEND_MS)
    

def _send_document(bot, subscriber_id, file_ids, least_ms):
    global _last_send_timestamp
    for file_id in file_ids:
        while (dt.datetime.utcnow() - _last_send_timestamp) < dt.timedelta(milliseconds=least_ms):
            pass
        bot.send_document(chat_id=str(subscriber_id), document=file_id)
        _last_send_timestamp = dt.datetime.utcnow()

def _send_message(bot, subscriber_id, msg, least_ms):
    global _last_send_timestamp
    while (dt.datetime.utcnow() - _last_send_timestamp) < dt.timedelta(milliseconds=least_ms):
        pass
    bot.send_message(chat_id=str(subscriber_id), text=msg, parse_mode='html')
    _last_send_timestamp = dt.datetime.utcnow()