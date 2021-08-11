from db.subscriber import Subscriber
from db.subscription import Subscription
from db.quiz import Quiz

subscribers: dict[int, Subscriber] = {}
subscriptions: dict[int, Subscription] = {}
quizzes: dict[int, Quiz] = {}

def add_subscriber(subscriber: Subscriber):
    subscribers[subscriber.id] = subscriber

def delete_subscriber(subscriber_id: int):
    if subscriber_id in subscribers:
        subscribers.pop(subscriber_id, None)

def add_subscription(subscription: Subscription):
    subscriptions[subscription.subscriber_id] = subscription

# subscriber can modify only one subscription at a time
def delete_subscription(subscriber_id: int):
    if subscriber_id in subscriptions:
        subscriptions.pop(subscriber_id, None)

# subscriber can take only one quiz at a time
def add_quiz(subscriber_id: int, quiz: Quiz):
    quizzes[subscriber_id] = quiz

def delete_quiz(subscriber_id: int):
    if subscriber_id in quizzes:
        quizzes.pop(subscriber_id, None)

def clean(subscriber_id: int):
    delete_subscriber(subscriber_id)
    delete_subscription(subscriber_id)
    delete_quiz(subscriber_id)