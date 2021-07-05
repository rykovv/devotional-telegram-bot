from db.base import Base

from sqlalchemy.dialects.postgresql import UUID
import uuid

from sqlalchemy import Column, String, Integer, Numeric, ForeignKey
from sqlalchemy.orm import relationship

class Subscription(Base):
    __tablename__ = 'subscriptions'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    subscriber_id = Column(Numeric, ForeignKey('subscribers.id'))
    # selected devotional name
    devotional_name = Column('devotional_name', String(128))
    
    # subscriber-defined preffered time to receive devotionals
    preferred_time = Column('preferred_time', String(10))
    # subscription creation time in UTC
    creation_utc = ('creation_utc', Numeric)

    def __init__(self, subscriber_id, devotional_name, preferred_time, creation_utc):
        self.subscriber_id = subscriber_id
        self.devotional_name = devotional_name
        self.preferred_time = preferred_time
        self.creation_utc = creation_utc