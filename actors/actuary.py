from db.base import Session

from db.devotional import Devotional
from db.subscriber import Subscriber
from db.subscription import Subscription
from db.statistics import Statistics

from utils.consts import STATISTICS_UNIQUE_ID
from utils.utils import get_epoch

def subscribers():
    session = Session()
    count = session.query(Subscriber).count()
    session.close()
    return count

def subscriptions():
    session = Session()
    count = session.query(Subscription).count()
    session.close()
    return count

def geo_skipped():
    session = Session()
    count = session.query(Subscriber).filter(Subscriber.time_zone == 'skipped').count()
    session.close()
    return count

def subscriptions_by_devotional():
    session = Session()
    sbd = {}
    devotionals = session.query(Devotional.name).distinct().all()[0]
    for devotional in devotionals:
        sbd[devotional] = session.query(Subscription).filter(Subscription.devotional_name == devotional).count()
    session.close()
    return sbd

def statistics_setup():
    session = Session()
    stats = session.query(Statistics).get(STATISTICS_UNIQUE_ID)
    if stats == None:
        session.add(Statistics())
        session.commit()
    session.close()

def statistics():
    session = Session()
    stats = session.query(Statistics).get(STATISTICS_UNIQUE_ID)
    session.close()
    return stats

def set_last_registered():
    session = Session()
    stats = session.query(Statistics).get(STATISTICS_UNIQUE_ID)
    stats.last_registered = get_epoch()
    session.commit()
    session.close()

def set_last_subscribed():
    session = Session()
    stats = session.query(Statistics).get(STATISTICS_UNIQUE_ID)
    stats.last_subscribed = get_epoch()
    session.commit()
    session.close()

def add_sent(tosum=1):
    session = Session()
    stats = session.query(Statistics).get(STATISTICS_UNIQUE_ID)
    stats.sent += tosum
    session.commit()
    session.close()

def add_unsubscribed():
    session = Session()
    stats = session.query(Statistics).get(STATISTICS_UNIQUE_ID)
    stats.unsubscribed += 1
    session.commit()
    session.close()


statistics_setup()