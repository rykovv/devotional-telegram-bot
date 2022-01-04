from db.base import Base

from sqlalchemy.dialects.postgresql import UUID
import uuid

from sqlalchemy import Column, Numeric, String
from sqlalchemy.types import JSON

class Promise(Base):
    __tablename__ = 'promises'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # promis for day # in original order (somewhat chronological)
    original_order = Column('original_order', Numeric)
    # promis for day # in random order
    random_order = Column('random_order', Numeric)
    # verse book number
    verse_bible_reference = Column('verse_bible_reference', String(32))
    
    # optional JSON field for possible extentions and adaptions
    optional = Column('optional', JSON)

    def __init__(self, original_order, random_order, verse_bible_reference, optional=None):
        self.original_order = original_order
        self.random_order = random_order
        self.verse_bible_reference = verse_bible_reference
        self.optional = optional