from db.base import Base

from sqlalchemy import Column, Numeric

from utils.consts import STATISTICS_UNIQUE_ID

class Statistics(Base):
    __tablename__ = 'statistics'
    
    # telegram user id
    id = Column(Numeric, primary_key = True)
    # UTC when last user was registered
    last_registered = Column('last_registered', Numeric)
    # UTC when last user was subscribed
    last_subscribed = Column('last_subscribed', Numeric)
    # Number of total sent devotionals
    sent = Column('sent', Numeric, default=0)
    # Number of unsubscribed usres
    unsubscribed = Column('unsubscribed', Numeric, default=0)
    # Number of completed quizzes
    quizzes = Column('quizzes', Numeric, default=0)
    # Number of Bible queries
    bible_queries = Column('bible_queries', Numeric, default=0)
    # Number of prophetic verse queries
    prophetic_queries = Column('prophetic_queries', Numeric, default=0)
    

    def __init__(self, id=STATISTICS_UNIQUE_ID):
        self.id = id