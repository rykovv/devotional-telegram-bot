from db.base import Session

from db.devotional import Devotional
from db.subscriber import Subscriber
from db.subscription import Subscription

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