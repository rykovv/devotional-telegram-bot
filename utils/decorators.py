from db.base import Session
from sqlalchemy.orm import Session as orm_session

# TODO: solve problem of generic return. when a tuple is returned by f
#       only the first value is unpacked, the rest is ignored 
def with_session(f):
    def _with_session(*args, **kwargs):
        session = Session()
        res = None

        try:
            res = f(session, *args, **kwargs)
        except Exception as error:
            print(error)
        else:
            session.commit()
        finally:
            session.close()
    
        return (res)
    return _with_session

def make_session_scope(orm_session):
    """Provide a transactional scope around a series of operations."""
    session = orm_session()
    session.expire_on_commit = False
    try:
        yield session
        session.commit()
    except:
        session.rollback()
        raise
    finally:
        session.close()

# with make_session_scope(Session) as session:
#     query = session.query(model)