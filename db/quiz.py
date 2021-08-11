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
    subscription_id = Column(Numeric, ForeignKey('subscriptions.id'))
    # Book name to which a quiz is related
    book_name = Column('book_name', String(256), nullable=False)
    # Study name to which a quiz is related
    study_name = Column('study_name', String(256))
    # study day related to a quiz
    day = Column('day', String(3), nullable=False)
    # chapter on which a quiz has been based
    chapter = Column('chapter', String(64))
    # numbers of questions within chapter
    questions_range = Column('chapter', String(10))

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


    def __init__(self, id, subscription_id, book_name, study_name, day, chapter, questions_range, total, chapter_quiz, completion_utc):
        self.id = id
        self.subscription_id = subscription_id
        self.book_name = book_name
        self.study_name = study_name
        self.day = day
        self.chapter = chapter
        self.questions_range = questions_range
        self.total = total
        self.chapter_quiz = chapter_quiz
        self.completion_utc = completion_utc
        self.current_question = 0

    def persist(self):
        session = Session()
        session.add(self)
        session.commit()
        session.close()

    def delete(self):
        session = Session()
        session.delete(self)
        session.commit()
        session.close()

    def finished(self) -> bool:
        return (self.current_question < self.total)

    def add_correct(self):
        session = Session()
        self.correct += 1
        session.add(self)
        session.commit()
        session.close()

    def add_wrong(self):
        session = Session()
        self.wrong += 1
        session.add(self)
        session.commit()
        session.close()

    def make_knowledge(self) -> int:
        session = Session()
        self.knowledge = self.correct/self.total
        self.completion_utc = get_epoch()
        session.add(self)
        session.commit()
        session.close()
        
        return int(self.knowledge*100)

    def get_questions_range(self) -> list[int]:
        snums = self.questions_range.split('-')
        return range(int(snums[0]), int(snums[1])+1)