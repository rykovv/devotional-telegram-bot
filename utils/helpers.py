from db.subscription import Subscription
from db.base import Session
from db.subscriber import Subscriber
import actors.actuary as actuary
import utils.buffer as buffer

def fetch_subscriber(id):
    session = Session()
    subscriber = session.query(Subscriber).get(id)
    session.close()

    return subscriber

def process_send_exception(exception, subscription):
    if str(exception) == 'Forbidden: bot was blocked by the user':
        session = Session()
        subscriber = session.query(Subscriber).get(subscription.subscriber_id)
        session.close()
        subscription.delete()
        subscriber.delete()
        actuary.add_unsubscribed()

        return 'Subscriber and subscription were deleted.'
    return 'No action taken at exception.'

def subscriptions_count(sid):
    session = Session()
    count = session.query(Subscription).filter(Subscription.subscriber_id == sid).count()
    session.close()
    return count

def persist_buffer(userid):
    if userid in buffer.subscribers:
        buffer.subscribers[userid].persist()
        actuary.set_last_registered()
    if userid in buffer.subscriptions:
        buffer.subscriptions[userid].persist()
        actuary.set_last_subscribed()

def clean_db(userid):
    if userid in buffer.subscriptions:
        buffer.subscriptions[userid].delete()
    if userid in buffer.subscribers:
        buffer.subscribers[userid].delete()