from db.base import Base

from sqlalchemy.dialects.postgresql import UUID
import uuid

from sqlalchemy import Column, String, Numeric
from sqlalchemy.types import JSON

class Book(Base):
    __tablename__ = 'books'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # book name
    name = Column('name', String(256))

    # chapter number
    chapter_number = Column('chapter_number', Numeric)
    # chapter title
    chapter_title = Column('chapter_title', String(768))
    # chapter paragraphs count
    paragraphs_count = Column('paragraphs_count', Numeric)
    # chapter paragraphs, actual content
    paragraphs = Column('paragraphs', JSON)

    # dict with urls to a media content for that chapter (i.e. youtube)
    urls = Column('urls', JSON)
    # dict of telegram file_ids for instant telegram sending
    telegram_file_ids = Column('telegram_file_ids', JSON)

    # optional field for any future adaptions
    optional = Column('optional', JSON)

    def __init__(self, name, chapter_number, chapter_title, paragraphs_count, paragraphs, urls, telegram_file_ids, optional=None):
        self.name = name
        self.chapter_number = chapter_number
        self.chapter_title = chapter_title
        self.paragraphs_count = paragraphs_count
        self.paragraphs = paragraphs
        self.urls = urls
        self.telegram_file_ids = telegram_file_ids
        self.optional = optional
