from db.base import Base, Session

from sqlalchemy import Column, String, Numeric
from sqlalchemy.orm import relationship

from utils.utils import get_epoch


class Subscriber(Base):
    __tablename__ = 'subscribers'
    
    # telegram user id
    id = Column(Numeric, primary_key = True)
    # subscriber time zone in string, e.g. 'America/Los_Angeles'
    time_zone = Column('time_zone', String(128))
    # subscriber creation date
    creation_utc = Column('creation_utc', Numeric)

    # foreign key relationship with subscriptions. on subscriber delete, 
    #   delete subscriptions in a cascade manner
    subscriptions = relationship('Subscription', 
                                cascade='all, delete, delete-orphan', 
                                lazy='joined', 
                                order_by='asc(Subscription.creation_utc)')

    def __init__(self, id, time_zone=None, creation_utc=get_epoch()):
        self.id = id
        self.time_zone = time_zone
        self.creation_utc = creation_utc

    def skipped_timezone(self):
        return self.time_zone == 'skipped'

    def persist(self):
        session = Session()
        session.add(self)
        session.commit()
        session.close()

    def delete(self):
        session = Session()
        session.delete(self)
        session.commit()
        session.close()

    def subscribed(self, title):
        for subscription in self.subscriptions:
            if subscription.title == title:
                return True
        return False

    def has_subscriptions(self):
        return (self.subscriptions != [])