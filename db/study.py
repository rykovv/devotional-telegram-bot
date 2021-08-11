from db.base import Base

from sqlalchemy.dialects.postgresql import UUID
import uuid

from sqlalchemy import Column, String, Numeric
from sqlalchemy.types import JSON

class Study(Base):
    __tablename__ = 'studies'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # book name on which a study is based
    book_name = Column('book_name', String(256))
    # study name
    study_name = Column('study_name', String(256))
    
    # chapter number
    chapter_number = Column('chapter_number', Numeric)
    # chapter title
    chapter_title = Column('chapter_title', String(768))
    # study day
    day = Column('day', Numeric)
    # study Bible verse
    verse = Column('verse', String(1024))
    # chapter paragraphs count
    paragraphs_count = Column('paragraphs_count', Numeric)
    # chapter paragraphs, actual content
    paragraphs = Column('paragraphs', JSON)
    # questions range related to a study day
    questions = Column('questions', String(10))

    # list of urls to media content for that study day (i.e. youtube)
    urls = Column('urls', JSON)
    # dict of telegram file_ids for instant telegram sending
    telegram_file_ids = Column('telegram_file_ids', JSON)

    # optional field for any future adaptions
    optional = Column('optional', JSON)


    def __init__(self, 
                id, 
                book_name, 
                study_name, 
                chapter_number, 
                chapter_title, 
                day,
                verse,
                paragraphs_count, 
                paragraphs,
                questions, 
                urls, 
                telegram_file_ids, 
                optional
    ):
        self.id = id
        self.book_name = book_name
        self.study_name = study_name
        self.chapter_number = chapter_number
        self.chapter_title = chapter_title
        self.day = day
        self.verse = verse
        self.paragraphs_count = paragraphs_count
        self.paragraphs = paragraphs
        self.questions = questions
        self.urls = urls
        self.telegram_file_ids = telegram_file_ids
        self.optional = optional

    def questions_range(self):
        snums = self.questions.split('-')
        return range(int(snums[0]), int(snums[1])+1)