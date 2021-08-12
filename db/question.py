from sqlalchemy.sql.sqltypes import Numeric
from db.base import Base

from sqlalchemy.dialects.postgresql import UUID
import uuid

from sqlalchemy import Column, String
from sqlalchemy.types import JSON

from string import ascii_lowercase
from utils.consts import QUESTIONS_BY_ROW

from utils.types import TelegramKeyboard

class Question(Base):
    __tablename__ = 'questions'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Book name related to a question
    book_name = Column('book_name', String(256), nullable=False)
    # Study name to which a question is related
    study_name = Column('study_name', String(256))
    # Book chapter from which the question has been taken
    chapter_number = Column('chapter_number', Numeric)
    # Question number within a chapter
    number = Column('number', Numeric, nullable=False)
    
    # Question text
    question = Column('question', String(1024), nullable=False)
    # Response options
    options = Column('options', JSON, nullable=False)
    # Correct option in letter format, i.e. a,b,c,d.
    correct_option = Column('correct_option', String(4), nullable=False)
    # Reference text with the correct option
    reference = Column('reference', String(2048))

    # optional field for possible future adaptions and extentions
    optional = Column('optional', JSON)


    def __init__(self, book_name, study_name, chapter_number, number, question, options, correct_option, reference, optional=None):
        self.book_name = book_name
        self.study_name = study_name
        self.chapter_number = chapter_number
        self.number = number
        self.question = question
        self.options = options
        self.correct_option = correct_option
        self.reference = reference
        self.optional = optional
        
    def test_response(self, response) -> bool:
        return response == self.correct_option

    def make_list_options(self) -> list[str]:
        options = []
        for i, option in enumerate(self.options):
            options.append(f'{ascii_lowercase[i]}. {option}')
        
        return options
    
    def make_str_options(self) -> str:
        options = ''
        for i, option in enumerate(self.options):
            options += f'{ascii_lowercase[i]}. {option}\n'
        return options

    def make_telegram_keyboard(self) -> TelegramKeyboard:
        kb = []
        for i in range(self.options):
            if i % QUESTIONS_BY_ROW == 0:
                kb.append([ascii_lowercase[i]])
            else:
                kb[i//QUESTIONS_BY_ROW].append(ascii_lowercase[i])

        return kb