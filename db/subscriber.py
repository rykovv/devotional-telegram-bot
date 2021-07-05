from db.base import Base

from sqlalchemy import Column, String, Integer, Numeric
from sqlalchemy.orm import relationship

class Subscriber(Base):
    __tablename__ = 'subscribers'
    
    # telegram user id
    id = Column(Numeric, primary_key = True)
    # user time zone in string, e.g. 'America/Los_Angeles'
    time_zone = Column('time_zone', String(128))
    # utc offset respect bot's location
    utc_offset = Column('utc_offset', Integer)
    # subscriber creation date
    creation_utc = Column('creation_utc', Numeric)

    # foreign key relationship with subscriptions. on subscriber delete, 
    #   delete subscriptions in a cascade manner
    subscriptions = relationship('Subscription', cascade='all, delete-orphan')

    def __init__(self, id, time_zone, utc_offset, creation_utc):
        self.id = id
        self.time_zone = time_zone
        self.utc_offset = utc_offset
        self.creation_utc = creation_utc