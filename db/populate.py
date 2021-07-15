from db.devotional import Devotional
from db.base import Session, engine, Base
import json
from configparser import ConfigParser
import utils.consts as consts
from utils.utils import get_logger

logger = get_logger()

# Deploy database schema if not done
Base.metadata.create_all(engine)

config = ConfigParser()
config.read(consts.CONFIG_FILE_NAME)

MARANATHA_FILE = f'{config["content"]["folder"]}/json/es_MSV76.json'

def populate_devotional_maranatha():
    session = Session()
    if not session.query(Devotional).filter(Devotional.name == '¡Maranata: El Señor Viene!').count() == 365:
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
                    audio_file_id=v['audio_file_id'], \
                    year_day=k
                )
            )
            session.commit()
    else:
        logger.info('¡Maranata: El Señor Viene! devotional is aready in the db.')
    session.close()

populate_devotional_maranatha()