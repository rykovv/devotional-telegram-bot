from sqlalchemy.sql.operators import op
from db.base import Base

from sqlalchemy.dialects.postgresql import UUID
import uuid

from sqlalchemy import Column, String, Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.types import JSON

class Devotional(Base):
    __tablename__ = 'devotionals'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # devotional name
    name = Column('name', String(256))

    # month and day corresponding to the devotional
    title_date = Column('title_day', String(512))
    title = Column('title', String(768))
    date = Column('date', String(128))
    month = Column('month', String(3))
    day = Column('day', String(3))
    verse = Column('verse', String(1024))
    paragraphs_count = Column('paragraphs_count', Numeric)
    paragraphs = Column('paragraphs', JSON)
    year_day = Column('year_day', Numeric)
    optional = Column('optional', String(128))

    # youtube link to that devotional
    url = Column('url', String(256))
    # telegram file_id for instant sending
    audio_file_ids = Column('audio_file_ids', JSON)

    def __init__(self, name, title_date, title, date, month, day, verse, paragraphs_count, paragraphs, url, audio_file_ids, year_day, optional):
        self.name = name
        self.title_date = title_date
        self.title = title
        self.date = date
        self.month = month
        self.day = day
        self.verse = verse
        self.paragraphs_count = paragraphs_count
        self.paragraphs = paragraphs
        self.url = url
        self.audio_file_ids = audio_file_ids
        self.year_day = year_day
        self.optional = optional

    def questions_range(self):
        snums = self.optional.split('-')
        return range(int(snums[0]), int(snums[1])+1)