from sqlalchemy.sql.sqltypes import Boolean
from db.base import Session
from db.subscription import Subscription
from db.subscriber import Subscriber
import actors.actuary as actuary

import utils.buffer as buffer
import utils.consts as consts


def fetch_subscriber(id) -> Subscriber:
    session = Session()
    subscriber = session.query(Subscriber).get(id)
    session.close()

    return subscriber


def process_send_exception(exception, subscription) -> str:
    if str(exception) == 'Forbidden: bot was blocked by the user':
        session = Session()
        subscriber = session.query(Subscriber).get(subscription.subscriber_id)
        session.close()
        subscription.delete()
        subscriber.delete()
        actuary.add_unsubscribed()

        return 'Subscriber and subscription were deleted.'
    return 'No action taken at exception.'


def subscriptions_count(sid) -> int:
    session = Session()
    count = session.query(Subscription).filter(Subscription.subscriber_id == sid).count()
    session.close()
    return count


def persist_buffer(userid) -> None:
    if userid in buffer.subscribers:
        buffer.subscribers[userid].persist()
        actuary.set_last_registered()
    if userid in buffer.subscriptions:
        buffer.subscriptions[userid].persist()
        actuary.set_last_subscribed()


def clean_db(userid) -> None:
    if userid in buffer.subscriptions:
        buffer.subscriptions[userid].delete()
    if userid in buffer.subscribers:
        buffer.subscribers[userid].delete()


def print_subscription(subscription: Subscription, skipped: Boolean = False) -> str:
    if skipped:
        return f'{subscription.devotional_name} cada día a la(s) {subscription.preferred_time_local} PST del día anterior.'
    else:
        return f'{subscription.devotional_name} cada día a la(s) {subscription.preferred_time_local}.'


def prepare_subscriptions_reply(subscriptions, str_only=False, kb_only=False, skipped=False):
    subscriptions_str = ''
    subscriptions_kb = []
    for i, subscription in enumerate(subscriptions):
        subscriptions_str += f'{i+1}. {print_subscription(subscription, skipped)}\n'
        if i % consts.SUBSCRIPTIONS_BY_ROW == 0:
            subscriptions_kb.append([str(i+1)])
        else:
            subscriptions_kb[i//consts.SUBSCRIPTIONS_BY_ROW].append(str(i+1))

    return (subscriptions_str if str_only else (subscriptions_kb if kb_only else subscriptions_str, subscriptions_kb))