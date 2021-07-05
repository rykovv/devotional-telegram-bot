import time

def get_epoch():
    return int(time.time())

# -07:00 -> -700
def utc_offset_to_int(offset):
    return int(''.join(offset.split(':')))

# def with_session(function):
#     session = Session()
#     def _with_session(update, context):
#         return function(update, context)
#     session.commit()
#     session.close()
#     return _with_session