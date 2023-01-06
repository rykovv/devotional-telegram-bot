from db.base import Base, Session

from sqlalchemy.dialects.postgresql import UUID
import uuid

from sqlalchemy import Column, String, Integer, Numeric, ForeignKey
from sqlalchemy.orm import relationship

from utils.utils import get_epoch, shift_12h_tf

class Subscription(Base):
    __tablename__ = 'subscriptions'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    subscriber_id = Column(Numeric, ForeignKey('subscribers.id'))
    # subscription title for the selected material
    title = Column('title', String(128))
    
    # subscriber-defined preffered time to receive readings
    preferred_time_local = Column('preferred_time_local', String(10))
    # system-translated preffered time to send readings
    preferred_time_utc = Column('preferred_time_utc', String(10))
    # utc offset respect bot's location
    utc_offset = Column('utc_offset', Integer)
    # subscription creation time in UTC
    creation_utc = Column('creation_utc', Numeric)

    # this relatoin is necessary for cascade drop on subscription removing.
    #   however, it is not necessary to load all the quizzes every time.
    quizzes = relationship('Quiz', cascade='all, delete, delete-orphan')

    # -700 is PST to UTC offset (in summer)
    def __init__(self, subscriber_id, title=None, preferred_time_local='10pm', utc_offset=-700, creation_utc=get_epoch()):
        self.subscriber_id = subscriber_id
        self.title = title
        self.preferred_time_local = preferred_time_local
        self.utc_offset = utc_offset
        self.preferred_time_utc = shift_12h_tf(preferred_time_local, utc_offset)
        self.creation_utc = creation_utc
        self.id = uuid.uuid4()

    def update_utc_offset(self, offset):
        self.utc_offset = offset
        self.preferred_time_utc = shift_12h_tf(self.preferred_time_local, self.utc_offset)
        
    def update_preferred_time_local(self, new_time):
        self.preferred_time_local = new_time
        self.preferred_time_utc = shift_12h_tf(self.preferred_time_local, self.utc_offset)
        
    # def persist(self, session):
    #     # session.add(self)
    #     session.merge(self)

    # def delete(self, session, id = None):
    #     if id == None:
    #         session.merge(self)
    #         session.delete(self)
    #     else:
    #         subscription = session.query(Subscription).get(id)
    #         session.delete(subscription)