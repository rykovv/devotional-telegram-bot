from db.base import Base

from sqlalchemy.dialects.postgresql import UUID
import uuid

from sqlalchemy import Column, String, Numeric
from sqlalchemy.types import JSON

class Bible(Base):
    __tablename__ = 'bible'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # book name
    book_name = Column('book_name', String(32))
    # book number
    book_number = Column('book_number', Numeric)
    # book abbreviation
    book_abbr = Column('book_abbr', String(5))

    # chapter number
    chapter_number = Column('chapter_number', Numeric)

    # verse chapter number
    verse_chapter_number = Column('verse_chapter_number', Numeric)
    # verse book number
    verse_book_number = Column('verse_book_number', Numeric)
    # verse book number
    verse_bible_number = Column('verse_bible_number', Numeric)
    # verse text
    verse = Column('verse', String(500))

    # dict with urs for different resources, i.e. YouTube
    urls = Column('urls', JSON)
    # dict of telegram file_ids for instant telegram sending
    telegram_file_ids = Column('telegram_file_ids', JSON)

    # optional JSON field for possible extentions and adaptions
    optional = Column('optional', JSON)

    def __init__(
        self, 
        book_name, 
        book_number, 
        book_abbr, 
        chapter_number,
        verse_chapter_number, 
        verse_book_number,
        verse_bible_number,
        verse,
        urls = None, 
        telegram_file_ids = None,
        optional=None
    ):
        self.book_name = book_name
        self.book_number = book_number
        self.book_abbr = book_abbr
        self.chapter_number = chapter_number
        self.verse_chapter_number = verse_chapter_number
        self.verse_book_number = verse_book_number
        self.verse_bible_number = verse_bible_number
        self.verse = verse
        self.urls = urls
        self.telegram_file_ids = telegram_file_ids
        self.optional = optional