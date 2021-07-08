import time

import utils.consts as consts

def get_epoch():
    return int(time.time())

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
    shifted_time_idx = (consts.TF_24TO12.index(tfrom)+hours) % 24
    
    if minutes != 0:
        if offset > 0:
            shifted_time_idx = (shifted_time_idx + 1) % 24
        else:
            shifted_time_idx = (shifted_time_idx - 1) % 24
            
    return consts.TF_24TO12[shifted_time_idx]
