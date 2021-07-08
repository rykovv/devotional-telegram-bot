from configparser import ConfigParser

import telegram
from db.base import Session
from utils.utils import get_current_utc_hour
import utils.consts as consts

from db.subscription import Subscription

config = ConfigParser()
config.read(consts.CONFIG_FILE_NAME)

def send():
    session = Session()
    current_hour = consts.TF_24TO12[get_current_utc_hour()]
    subscriptions = session.query(Subscription).filter(Subscription.preferred_time_utc == current_hour).all()

    bot = telegram.Bot(token=config['bot']['token'])
    msg = 'That\'s today\'s devotional!'

    for subscription in subscriptions:
        bot.sendMessage(chat_id=str(subscription.subscriber_id), text=msg, parse_mode=telegram.ParseMode.HTML)

    print(f'devotionals sent at {consts.TF_24TO12[get_current_utc_hour()]}')