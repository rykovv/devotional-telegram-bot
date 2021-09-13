### The file was in the project root directory when exectued. 

from db.devotional import Devotional
from db.subscriber import Subscriber
from db.subscription import Subscription

from db.base import Session, engine, Base

from utils.utils import get_epoch

# generate database schema
Base.metadata.create_all(engine)

# create a new session
session = Session()

# create subscribers
pedro = Subscriber(id=1234567890, time_zone='America/Los_Angeles', utc_offset=-7000, creation_utc=get_epoch())
tobias = Subscriber(id=1234567891, time_zone='Asia/Russia', utc_offset=3000, creation_utc=get_epoch())
naara = Subscriber(id=1234567892, time_zone='Europe/Spain', utc_offset=1000, creation_utc=get_epoch())

# create devotionals
maranatha11 = Devotional(name='Maranatha!', month=1, day=1, link='link1', text=None, title=None)
maranatha12 = Devotional(name='Maranatha!', month=1, day=2, link='link2', text=None, title=None)
lift_him_up = Devotional(name='Lift Him Up!', month=1, day=1, link='link3', text=None, title=None)

# create subscriptions
pedro_subscription = Subscription(subscriber_id=pedro.id, title='Maranatha!', preferred_time='7am', creation_utc=get_epoch())
tobias_subscription = Subscription(subscriber_id=tobias.id, title='Maranatha!', preferred_time='11am', creation_utc=get_epoch())
naara_subscription = Subscription(subscriber_id=naara.id, title='Lift Him Up!', preferred_time='10pm', creation_utc=get_epoch())

# persistance
session.add(pedro)
session.add(tobias)
session.add(naara)

session.add(maranatha11)
session.add(maranatha12)
session.add(lift_him_up)

session.add(pedro_subscription)
session.add(tobias_subscription)
session.add(naara_subscription)

session.commit()
session.close()