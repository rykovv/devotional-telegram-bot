from db.base import Session
from db.subscriber import Subscriber

def fetch_subscriber(id):
    session = Session()
    subscriber = session.query(Subscriber).get(id)
    session.close()

    return subscriber