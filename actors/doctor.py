from datetime import datetime, timedelta

from actors.sender import last_send_ts, report_exception
from actors.scheduler import scheduler_catch_exception

last_health_check = None
last_send_none_ts = None

@scheduler_catch_exception
def health_check():
    if last_send_ts is not None:
        past = datetime.now() - last_send_ts
        if past > timedelta(hours=1, minutes=10):
            # failed send thread detected
            report_exception(f'{past} past last send time. Probably sender.send() broke. Last sent: {last_send_ts}')
    else:
        if last_send_none_ts is None:
            last_send_none_ts = datetime.now()

        if last_health_check is not None:
            since_last_send_ts_none = datetime.now() - last_send_none_ts
            if since_last_send_ts_none > timedelta(hours=1, minutes=10):
                report_exception(f'Send was not run since the bot started: {since_last_send_ts_none}')

    last_health_check = datetime.now()