import re
import utils.consts as consts
from utils.utils import shift_12h_tf


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
