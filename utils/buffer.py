
subscribers = {}
subscriptions = {}


def add_subscriber(subscriber):
    subscribers[subscriber.id] = subscriber

def delete_subscriber(subscriber_id):
    if subscriber_id in subscribers:
        subscribers.pop(subscriber_id, None)

def add_subscription(subscription):
    subscriptions[subscription.subscriber_id] = subscription

# subscriber can modify only one subscription at a time
def delete_subscription(subscriber_id):
    if subscriber_id in subscriptions:
        subscriptions.pop(subscriber_id, None)

def clean(subscriber_id):
    delete_subscriber(subscriber_id)
    delete_subscription(subscriber_id)