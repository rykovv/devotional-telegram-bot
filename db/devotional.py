from sqlalchemy.sql.operators import op
from db.base import Base

from sqlalchemy.dialects.postgresql import UUID
import uuid

from sqlalchemy import Column, String, Numeric
from sqlalchemy.types import JSON

class Devotional(Base):
    __tablename__ = 'devotionals'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # devotional name
    name = Column('name', String(256))

    # written in original language month and day
    title_date = Column('title_day', String(512))
    # day title
    title = Column('title', String(768))
    # written date in original language
    date = Column('date', String(128))
    # month parsed from the date
    month = Column('month', Numeric)
    # day parsed from the day
    day = Column('day', Numeric)
    # day Bible verse
    verse = Column('verse', String(1024))
    # paragraphs count in a devotional
    paragraphs_count = Column('paragraphs_count', Numeric)
    # devotional text, actual content
    paragraphs = Column('paragraphs', JSON)
    # year day of the devotional
    year_day = Column('year_day', Numeric)

    # dict with urs for different resources, i.e. YouTube
    urls = Column('urls', JSON)
    # dict of telegram file_ids for instant telegram sending
    telegram_file_ids = Column('telegram_file_ids', JSON)

    # optional JSON field for possible extentions and adaptions
    optional = Column('optional', JSON)

    def __init__(
        self, 
        name, 
        title_date, 
        title, 
        date, 
        month, 
        day, 
        verse, 
        paragraphs_count, 
        paragraphs, 
        urls, 
        telegram_file_ids, 
        year_day, 
        optional=None
    ):
        self.name = name
        self.title_date = title_date
        self.title = title
        self.date = date
        self.month = month
        self.day = day
        self.verse = verse
        self.paragraphs_count = paragraphs_count
        self.paragraphs = paragraphs
        self.urls = urls
        self.telegram_file_ids = telegram_file_ids
        self.year_day = year_day
        self.optional = optional