from db.base import Base, Session

from sqlalchemy.dialects.postgresql import UUID
import uuid

from sqlalchemy import Column, String, Integer, Numeric, ForeignKey
from sqlalchemy.orm import relationship

from utils.utils import get_epoch

class Subscription(Base):
    __tablename__ = 'subscriptions'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    subscriber_id = Column(Numeric, ForeignKey('subscribers.id'))
    # selected devotional name
    devotional_name = Column('devotional_name', String(128))
    
    # subscriber-defined preffered time to receive devotionals
    preferred_time = Column('preferred_time', String(10))
    # subscription creation time in UTC
    creation_utc = Column('creation_utc', Numeric)

    def __init__(self, subscriber_id, devotional_name=None, preferred_time=None, creation_utc=None):
        self.subscriber_id = subscriber_id
        self.devotional_name = devotional_name
        self.preferred_time = preferred_time
        self.creation_utc = creation_utc

    def persist(self):
        session = Session()
        session.add(self)
        self.creation_utc = get_epoch()
        session.commit()
        session.close()

    def delete(self):
        session = Session()
        session.delete(self)
        session.commit()
        session.close()