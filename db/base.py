from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from configparser import ConfigParser

CONFIG_FILE_NAME = 'config.ini'

config = ConfigParser()
config.read(CONFIG_FILE_NAME)

engine = create_engine(f'postgresql://{config["database"]["user"]}:{config["database"]["password"]}@{config["database"]["address"]}:{config["database"]["port"]}/{config["database"]["name"]}')
Session = sessionmaker(bind = engine)

Base = declarative_base()

# Deploy database schema if not done
Base.metadata.create_all(engine)