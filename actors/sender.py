from configparser import ConfigParser

import telegram
from db.base import Session
from utils.utils import get_current_utc_hour, get_today_month_day
import utils.consts as consts

from db.subscription import Subscription

import actors.composer as composer

config = ConfigParser()
config.read(consts.CONFIG_FILE_NAME)

def send():
    session = Session()
    current_hour = consts.TF_24TO12[get_current_utc_hour()]
    subscriptions = session.query(Subscription).filter(Subscription.preferred_time_utc == current_hour).all()

    bot = telegram.Bot(token=config['bot']['token'])
    now = get_today_month_day()

    for subscription in subscriptions:
        msg, title = composer.compose(subscription.devotional_name, now[0], now[1])
        bot.send_message(chat_id=str(subscription.subscriber_id), text=msg, parse_mode='html')
        bot.send_audio(chat_id=str(subscription.subscriber_id), audio=open(f'files/mp3/maranata/{now[0]}/{now[1]}.mp3', 'rb'), title=title, timeout=300)

    print(f'devotionals sent at {consts.TF_24TO12[get_current_utc_hour()]}')