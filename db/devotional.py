from db.base import Base

from sqlalchemy.dialects.postgresql import UUID
import uuid

from sqlalchemy import Column, String, Numeric
from sqlalchemy.orm import relationship

class Devotional(Base):
    __tablename__ = 'devotionals'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # devotional name
    name = Column('name', String(128))

    # month and day corresponding to the devotional
    month = Column('month', Numeric)
    day = Column('day', Numeric)
    
    # youtube link to that devotional
    link = Column('link', String(256))

    # title and text for that day
    title = Column('title', String(200))
    text = Column('text', String(5000))

    def __init__(self, name, month, day, link, text, title):
        self.name = name
        self.month = month
        self.day = day
        self.link = link
        self.text = text
        self.title = title