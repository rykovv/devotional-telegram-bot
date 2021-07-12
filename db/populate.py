from db.devotional import Devotional
from db.base import Session
import json

MARANATHA_FILE = 'files/json/es_MSV76.json'

session = Session()

devotionals = {}

with open(MARANATHA_FILE, 'rb') as fp:
    devotionals = json.load(fp)

for k, v in devotionals.items():
    session.add(
        Devotional(
            name='¡Maranata: El Señor Viene!', \
            title_date=v['title_date'], \
            title=v['title'], \
            date=v['date'], \
            month=v['month'], \
            day=v['day'], \
            verse=v['verse'], \
            paragraphs_count=v['paragraphs_count'], \
            paragraphs=v['paragraphs'], \
            url=v['url'], \
            year_day=k
        )
    )
    session.commit()
session.close()