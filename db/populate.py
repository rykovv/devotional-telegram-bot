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
CS_FILE = f'{config["content"]["folder"]}/json/es_CS.json'

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
                    audio_file_ids=v['audio_file_ids'], \
                    year_day=k
                )
            )
            session.commit()
    else:
        logger.info('¡Maranata: El Señor Viene! devotional is aready in the db.')
    session.close()


def populate_book_conflict_of_ages():
    session = Session()
    if not session.query(Devotional).filter(Devotional.name == 'El Conflicto de los Siglos').count() == 43:
        chapters = {}

        with open(CS_FILE, 'rb') as fp:
            chapters = json.load(fp)

        for k, v in chapters.items():
            session.add(
                Devotional(
                    name='El Conflicto de los Siglos', \
                    title_date=None, \
                    title=v['title'], \
                    verse=v['chapter'], \
                    date=None, \
                    month=None, \
                    day=k, \
                    paragraphs_count=v['paragraphs_count'], \
                    paragraphs=v['paragraphs'], \
                    url=v['url'], \
                    audio_file_ids=v['audio_file_ids'], \
                    year_day=None
                )
            )
            session.commit()
    else:
        logger.info('El Conflicto de los Siglos book is aready in the db.')
    session.close()

populate_devotional_maranatha()
populate_book_conflict_of_ages()