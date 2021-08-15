from db.base import Session

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
    
        return res
    return _with_session