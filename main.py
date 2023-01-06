import threading

from bot_main import main

import actors.sender as sender
from actors.scheduler import run

import schedule

import utils.consts as consts

from configparser import ConfigParser
config = ConfigParser()
config.read(consts.CONFIG_FILE_NAME)

# from utils.status import status

def health_checker():
    print ('check status')


if __name__ == '__main__':
    # thread stubs
    th_sender = threading.Thread(target=sender.send)
    th_health_checker = threading.Thread(target=health_checker)

    # prepare tasks list
    #  1) health checker task that makes sure everything has been sent
    #     needs to be a thread because may require message sending
    #  2) new thread launch on every send time
    tasks = [
        {
            'every' : schedule.every(1).minutes if config['deployment']['build'] == 'production' else schedule.every(20).seconds,
            'task' : th_health_checker.start
        },
        {
            'every' : schedule.every().hour.at(':00') if config['deployment']['build'] == 'production' else schedule.every(30).seconds,
            'task' : th_sender.start
        }
    ]

    th_scheduler = threading.Thread(target=run, args=tasks)
    
    # start the Telegram Bot
    main()