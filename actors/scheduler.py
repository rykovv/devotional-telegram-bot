import threading
import time
import functools

from configparser import ConfigParser

import schedule
import utils.consts as consts
from utils.utils import get_logger

config = ConfigParser()
config.read(consts.CONFIG_FILE_NAME)

cease_continuous_run = threading.Event()


# def scheduler_catch_exception(cancel_on_failure: bool = False):
#     """ Decorator for catching exceptions for scheduled tasks.

#     Args:
#         cancel_on_failure (bool, optional): Cancel scheduler on failure. Defaults to False.
#     """
def catch_exceptions_decorator(job_func):
    @functools.wraps(job_func)
    def wrapper(*args, **kwargs):
        try:
            return job_func(*args, **kwargs)
        except Exception as e:
            import traceback
            logger = get_logger()
            tb = ''.join(traceback.format_exception(None, e, e.__traceback__))
            logger.error(f'Entered exception hander for one of the threads with following traceback:\n{tb}')
            # never cancel on failure
            # if cancel_on_failure:
            #     return schedule.CancelJob
    return wrapper
    # return catch_exceptions_decorator


def run_continuously(interval=1):
    """Continuously run, while executing pending jobs at each
    elapsed time interval.

    @return cease_continuous_run: threading. Event which can
    be set to cease continuous run. Please note that it is
    *intended behavior that run_continuously() does not run
    missed jobs*. For example, if you've registered a job that
    should run every minute and you set a continuous run
    interval of one hour then your job won't be run 60 times
    at each interval but only once.
    """

    class ScheduleThread(threading.Thread):
        @classmethod
        def run(cls):
            while not cease_continuous_run.is_set():
                schedule.run_pending()
                time.sleep(interval)

    continuous_thread = ScheduleThread()
    continuous_thread.start()


# Start the background thread
def run(tasks: dict, interval=1):
    # Schedule devotional sending every hour at 00th minute
    for task_name, task in tasks.items():
        if task_name == 'send':
            if config['deployment']['build'] == 'production':
                schedule.every().hour.at(':00').do(task)
            elif config['deployment']['build'] == 'test':
                schedule.every(30).seconds.do(task)
        elif task_name == 'health_check':
            if config['deployment']['build'] == 'production':
                schedule.every(5).minutes.do(task)
            elif config['deployment']['build'] == 'test':
                schedule.every(40).seconds.do(task)

    run_continuously(interval)


# Stop the background thread
def stop():
    cease_continuous_run.set()


