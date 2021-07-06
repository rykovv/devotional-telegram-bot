from db.base import Base, Session

from sqlalchemy import Column, String, Integer, Numeric
from sqlalchemy.orm import relationship

from utils.utils import get_epoch


class Subscriber(Base):
    __tablename__ = 'subscribers'
    
    # telegram user id
    id = Column(Numeric, primary_key = True)
    # subscriber first name
    first_name = Column('first_name', String(128))
    # subscriber time zone in string, e.g. 'America/Los_Angeles'
    time_zone = Column('time_zone', String(128))
    # utc offset respect bot's location
    utc_offset = Column('utc_offset', Integer)
    # subscriber creation date
    creation_utc = Column('creation_utc', Numeric)

    # foreign key relationship with subscriptions. on subscriber delete, 
    #   delete subscriptions in a cascade manner
    subscriptions = relationship('Subscription', cascade='all, delete, delete-orphan', lazy='joined')

    def __init__(self, id, first_name=None, time_zone=None, utc_offset=None, creation_utc=get_epoch()):
        self.id = id
        self.first_name = first_name
        self.time_zone = time_zone
        self.utc_offset = utc_offset
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