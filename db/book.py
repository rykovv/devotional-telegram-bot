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
    chapter_number = Column('chapter_number', String(5))
    # chapter title
    chapter_title = Column('chapter_title', String(768))
    # chapter paragraphs count
    paragraphs_count = Column('paragraphs_count', Numeric)
    # chapter paragraphs, actual content
    paragraphs = Column('paragraphs', JSON)

    # url to a media content for that chapter (i.e. youtube)
    url = Column('url', String(512))
    # list of telegram file_ids for instant telegram sending
    audio_file_ids = Column('audio_file_ids', JSON)

    # optional field for any future adaptions
    optional = Column('optional', JSON)

    def __init__(self, id, name, chapter_number, title, paragraphs_count, paragraphs, url, audio_file_ids, optional):
        self.id = id
        self.name = name
        self.chapter_number = chapter_number
        self.title = title
        self.paragraphs_count = paragraphs_count
        self.paragraphs = paragraphs
        self.url = url
        self.audio_file_ids = audio_file_ids
        self.optional = optional
