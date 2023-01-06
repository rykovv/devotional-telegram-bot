import threading
import time

from configparser import ConfigParser

import schedule
import utils.consts as consts

config = ConfigParser()
config.read(consts.CONFIG_FILE_NAME)

cease_continuous_run = threading.Event()

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
def run(tasks, interval=1):
    for task in tasks:
        task['every'].do(task['task'])
    
    # Schedule devotional sending every hour at 00th minute
    # if config['deployment']['build'] == 'production':
    #     schedule.every().hour.at(':00').do(task)
    # elif config['deployment']['build'] == 'test':
    #     schedule.every(30).seconds.do(task)
        
    run_continuously(interval)


# Stop the background thread
def stop():
    cease_continuous_run.set()


