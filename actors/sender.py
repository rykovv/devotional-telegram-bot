from configparser import ConfigParser

import telegram
from db.base import Session
from db.promise import Promise

import utils.consts as consts
from utils.utils import (
    extract_material_name,
    get_current_utc_hour,
    get_send_month_day,
    get_logger,
    days_since_epoch,
)
from utils.helpers import (
    process_send_exception,
    subscriptions_count,
    fetch_subscriber,
    check_send_date,
)

from db.subscription import Subscription
from db.devotional import Devotional
from db.book import Book
from db.study import Study

import actors.composer as composer
import actors.actuary as actuary

from actors.scheduler import scheduler_catch_exception

import time
import datetime as dt

config = ConfigParser()
config.read(consts.CONFIG_FILE_NAME)

logger = get_logger()
_last_send_timestamp = dt.datetime.utcnow()

last_send_ts = None


@scheduler_catch_exception
def send(all=False, month=None, day=None, chat_id=None):
    session = Session()
    if not all:
        current_hour = consts.TF_24TO12[get_current_utc_hour()]
        subscriptions = session.query(Subscription).filter(Subscription.preferred_time_utc.ilike(f'{current_hour}%')).all()
    else:
        subscriptions = session.query(Subscription).all()

    bot = telegram.Bot(token=config['bot']['token'])
    
    sent = 0
    retries = 0
    date = {'month' : month, 'day' : day}
    # must assure max sending of 30 messages per second, that's 33.33ms per message
    for subscription in subscriptions:
        done = False
        while not done:
            try:
                # check if the subscription is up to date
                if not _expired_subscription(subscription):
                    date = check_send_date(subscription, month, day)
                        
                    # compose a formatted message
                    msg, file_ids = composer.compose(subscription.title, 
                                                    date['month'], date['day'],
                                                    days_since_epoch(subscription.creation_utc))

                    # send files if available and if not a devotional
                    if not subscription.title in consts.LIST_OF_DEVOTIONALS:
                        _send_document(bot, subscription.subscriber_id, file_ids, consts.LEAST_BOT_SEND_MS)

                    # send text next to the files
                    _send_message(bot, subscription.subscriber_id, msg, consts.LEAST_BOT_SEND_MS)
                    
                    sent += 1
                else:
                    msg =   'Querido hermano/hermana,\n\n' \
                            'Ya ha pasado un año desde que Usted está recibiendo los devocionales ' \
                            f'{subscription.title}. Nos alegra inmensamente que ha podido ' \
                            'disfrutar de su suscripción y nuestros esfuerzos le han ayudado.\n\n' \
                            'Ahora llegó el momento de anular su suscripción. Si Usted desea ' \
                            'seguir recibiendo los devocionales, puede hacerlo con una nueva ' \
                            'suscripción marcando /start. Hemos estado trabajando para añadir más devocionales.\n\n' \
                            '¡Un gran saludo en Cristo!\n' \
                            'El equipo de Una Mirada de Fe y Esperanza'
                    _send_message(bot, subscription.subscriber_id, msg, consts.LEAST_BOT_SEND_MS)
                    
                    subscription.delete(session, id=subscription.id)

                done = True
            except Exception as e:
                action_taken, done = process_send_exception(e, subscription, session)
                report_exception(f'{e} sending at {date} to {str(subscription.subscriber_id)}.'
                                 f'\nAction: {action_taken}')
                time.sleep(pow(2, retries) if retries < 9 else consts.MAX_RESEND_DELAY)
                retries += 1
                
                if not done:
                    done = retries > consts.MAX_SEND_RETRIES
                
    session.close()

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
            logger.info(f'{sent} devotionals sent at {consts.TF_24TO12[get_current_utc_hour()]} with {retries} retries.')
        else:
            logger.info(f'Devotionals have been sent to all users at {consts.TF_24TO12[get_current_utc_hour()]} with {retries} retries.')

    last_send_ts = dt.datetime.now()


def send_global_message(msg):
    session = Session()
    subscriptions = session.query(Subscription).all()

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
                report_exception(f'{e} sending at {get_current_utc_hour()} to {str(subscription.subscriber_id)}.'
                                 f'\nAction: {process_send_exception(e, subscription, session)}')
                time.sleep(pow(2, retries) if retries < 9 else consts.MAX_RESEND_DELAY)
                retries += 1
                done = retries > consts.MAX_SEND_RETRIES

    session.close()

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
    logger.error(f'Reporting exception: {str(exception)}.')
    _send_message(bot, config['admin']['chat_id'], str(exception), consts.LEAST_BOT_SEND_MS)
    

def _send_document(bot, subscriber_id, file_ids, least_ms):
    # do not send documents in test deployment, they are binded to the production bot
    if config['deployment']['build'] != 'test':
        global _last_send_timestamp
        # send files without order. see json structure for order
        for file_id_list in file_ids.values():
            for file_id in file_id_list:
                while (dt.datetime.utcnow() - _last_send_timestamp) < dt.timedelta(milliseconds=least_ms):
                    pass
                bot.send_document(chat_id=str(subscriber_id), document=file_id)
                _last_send_timestamp = dt.datetime.utcnow()


def _send_message(bot, subscriber_id, msg, least_ms):
    global _last_send_timestamp
    to_send = len(msg)
    i = 0
    while to_send > 0:
        if to_send > telegram.constants.MAX_MESSAGE_LENGTH:
            while (dt.datetime.utcnow() - _last_send_timestamp) < dt.timedelta(milliseconds=least_ms):
                pass
            bot.send_message(chat_id=str(subscriber_id), text=msg[i*telegram.constants.MAX_MESSAGE_LENGTH:(i+1)*telegram.constants.MAX_MESSAGE_LENGTH], parse_mode='html')
            _last_send_timestamp = dt.datetime.utcnow()
        else:
            while (dt.datetime.utcnow() - _last_send_timestamp) < dt.timedelta(milliseconds=least_ms):
                pass
            bot.send_message(chat_id=str(subscriber_id), text=msg[i*telegram.constants.MAX_MESSAGE_LENGTH:], parse_mode='html')
            _last_send_timestamp = dt.datetime.utcnow()
        to_send -= telegram.constants.MAX_MESSAGE_LENGTH
        i += 1


def _expired_subscription(subscription):
    session = Session()
    count = 999
    material_name = extract_material_name(subscription.title)
    if consts.MATERIAL_TYPES[subscription.title] == 'Devotional':
        count = session.query(Devotional).filter(Devotional.name == material_name).count()
    elif consts.MATERIAL_TYPES[subscription.title] == 'Book':
        count = session.query(Book).filter(Book.name == material_name).count()
    elif consts.MATERIAL_TYPES[subscription.title] == 'Study':
        count = session.query(Study).filter(Study.book_name == material_name).count()
    elif consts.MATERIAL_TYPES[subscription.title] == 'Promise':
        count = session.query(Promise).count()
    session.close()
    return (days_since_epoch(subscription.creation_utc)+1 > count)