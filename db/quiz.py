from utils.utils import get_epoch
from sqlalchemy.sql.sqltypes import Boolean
from db.base import Base, Session

from sqlalchemy import Column, String, Numeric, ForeignKey, Float, Boolean

from sqlalchemy.dialects.postgresql import UUID
import uuid


class Quiz(Base):
    __tablename__ = 'quizzes'
    
    # quiz result id
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # subscription id. All quizzes are related to some subscription. 
    #   Subscruotion represents a study/reading
    subscription_id = Column(UUID(as_uuid=True), ForeignKey('subscriptions.id'))
    # Book name to which a quiz is related
    book_name = Column('book_name', String(256), nullable=False)
    # Study name to which a quiz is related
    study_name = Column('study_name', String(256))
    # study day related to a quiz
    day = Column('day', Numeric, nullable=False)
    # chapter number on which a quiz has been based
    chapter = Column('chapter', Numeric)
    # numbers of questions within chapter
    questions = Column('questions', String(10))

    # correct answers counter
    correct = Column('correct', Numeric, default=0)
    # wrong answers counter
    wrong = Column('wrong', Numeric, default=0)
    # total amount of questions
    total = Column('total', Numeric)
    # average knowledge persantage. marked when the quiz has been finished
    knowledge = Column('knowledge', Float, default=0)

    chapter_quiz = Column('chapter_quiz', Boolean, default=False)

    # subscriber creation date
    completion_utc = Column('completion_utc', Numeric, default=get_epoch())

    # local variable
    current_question = 0
    questions_range = []


    def __init__(
        self, 
        subscription_id, 
        book_name, 
        study_name, 
        day, 
        chapter, 
        questions, 
        questions_range, 
        total, 
        chapter_quiz, 
        completion_utc
    ):
        self.subscription_id = subscription_id
        self.book_name = book_name
        self.study_name = study_name
        self.day = day
        self.chapter = chapter
        self.questions = questions
        self.questions_range = questions_range
        self.total = total
        self.chapter_quiz = chapter_quiz
        self.completion_utc = completion_utc
        self.current_question = 0
        self.correct = 0
        self.wrong = 0
        self.knowledge = .0

    def finished(self) -> bool:
        return (self.current_question >= self.total)

    def add_correct(self):
        self.correct += 1
        
    def add_wrong(self):
        self.wrong += 1
        
    def make_knowledge(self) -> int:
        self.knowledge = (self.correct/self.total)*100
        self.completion_utc = get_epoch()
        
        return int(self.knowledge*100)