import re
import utils.consts as consts
from utils.utils import shift_12h_tf
import actors.composer as composer
import random
import json


def test_shift_12h_tf():
    from utils.consts import TF_24TO12
    for i in range(24):
        print(TF_24TO12[i], shift_12h_tf(TF_24TO12[i], -700))


def test_12h_tf() -> None:
    pattern = '^\d(\d)?(a|p)+m$'
    test_string = '5pm'
    result = re.match(pattern, test_string)

    if result:
        print("Search successful.")
    else:
        print("Search unsuccessful.")


def test_subscription_select_pattern():
    test_string = '2'
    result = re.match(consts.SUBSCRIPTION_SELECT_PATTERN, test_string)

    if result:
        print("Search successful.")
    else:
        print("Search unsuccessful.")

def test_composer():
    # compose a formatted message
    msg, file_ids = composer.compose(subscription_title=consts.DEVOTIONALS_KEYBOARD[0][0], 
                                    month=7, day=30,
                                    cron_day=2)

    # send files if available
    print(file_ids, type(file_ids))
    print(msg)

def promises_proc():
    promises = []
    promises_up = []
    with open('files/json/es_365_promises.json', 'rb') as fp:
        promises = json.load(fp)
    random.seed(1)
    random_order = random.sample(range(1, len(promises)+1), len(promises))
    for i, promise in enumerate(promises, start=1):
        promises_up.append({
            "original_order" : i,
            "verse_bible_reference" : promise["verse_bible_reference"],
            "random_order" : random_order[i-1]
        })
    with open('files/json/es_365_promises_up.json', 'wb+') as fp:
        fp.write(json.dumps(promises_up, ensure_ascii=False, indent = 2, separators=(',', ': ')).encode('utf-8'))

def bible_verse_reference_parse(ref):
    s = ref.split(':')
    book = ' '.join(s[0].split(' ')[:-1])
    chapter = int(s[0].split(' ')[-1])
    verses = []
    for v in s[1].split(','):
        if v.find('-') >= 0:
            verses.append([int(v.split('-')[0]), int(v.split('-')[1])])
        else:
            verses.append([int(v)])
    return book, chapter, verses

def test_promises():
    for i in range(367):
        msg, file_ids = composer.compose(subscription_title=consts.DEVOTIONALS_KEYBOARD[3][0], 
                                    month=7, day=30,
                                    cron_day=i+1)
        if msg[0] == '😞':
            print(i, msg)