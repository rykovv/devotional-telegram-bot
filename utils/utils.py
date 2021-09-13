from configparser import ConfigParser

import time
import datetime as dt
import logging

import utils.consts as consts

config = ConfigParser()
config.read(consts.CONFIG_FILE_NAME)

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

def get_epoch():
    return int(time.time())

def epoch_to_date(epoch):
    return time.strftime('%Y/%m/%d %H:%M:%S', time.localtime(epoch))

# -07:00 -> -700
def utc_offset_to_int(offset):
    return int(''.join(offset.split(':')))

def shift_12h_tf(tfrom, offset):
    """! Shifts time in 12-hour time format.
    @param tfrom    The input time to shift in 12-hour format, 
                    e.g. '12am', '2pm'.
    @param offset   The shift integer value of an input time.
                    1200 means 12-hours positive shift,
                    -730 means 7-hours 30-minutes negative shift.
    @return         The shifted time in 12-hour format.
    """
    hours = int(offset/100)
    minutes = abs(offset)%100
    shifted_time_idx = (consts.TF_24TO12.index(tfrom)-hours) % 24

    if minutes != 0:
        if offset > 0:
            shifted_time_idx = (shifted_time_idx - 1) % 24
        else:
            shifted_time_idx = (shifted_time_idx + 1) % 24
            
    sh = ''
    if hours > 0:
        if shifted_time_idx > consts.TF_24TO12.index(tfrom):
            sh = '+'
    else:
        if shifted_time_idx < consts.TF_24TO12.index(tfrom):
            sh = '-'
        
    return (consts.TF_24TO12[shifted_time_idx]+sh)

def get_current_utc_hour():
    return dt.datetime.utcnow().hour

def get_send_month_day(preferred_time, skipped=False):
    sendutc = dt.datetime.utcnow()
    
    if preferred_time[-1] == '-' and not skipped:
        sendutc -= dt.timedelta(days=1)
    elif preferred_time[-1] == '+':
        sendutc += dt.timedelta(days=1)

    return {'month':sendutc.month, 'day':sendutc.day}

def get_logger():
    return logging.getLogger(__name__)

def is_admin(chat_id):
    return (str(chat_id) == config['admin']['chat_id'])

def admin_message_formatter(msg):
    """! Formats received message into human-readable format.
    @param msg      Received unformatted text.
    @return         Well-formatted and prepared for further
                    sending message.
    @note           '#' for new line
                    '-' for list
    """
    formatted_msg = msg.replace('#', '\n')
    formatted_msg = formatted_msg.replace(' - ', '\n - ')
    return formatted_msg

def days_since_epoch(epoch):
    start = dt.datetime.fromtimestamp(epoch)
    now = dt.datetime.utcnow()
    return (now - start).days

def extract_material_name(subscription_name: str) -> str:
    category_name = subscription_name.split(':', 1)
    return category_name[0] if len(category_name) < 2 else category_name[1].strip()

def extract_material_type(subscription_title: str) -> str:
    pass

# make inclusive range from str, e.g. 1-3 -> [1,2,3]
def make_inclusive_range(str) -> list[int]:
    snums = str.split('-')
    return range(int(snums[0]), int(snums[1])+1)