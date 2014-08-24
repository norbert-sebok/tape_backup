# -----------------------------------------------------------------------------
# IMPORTS

# Standard library imports
import os

# Related third party imports
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Local application/library specific imports
import config


# -----------------------------------------------------------------------------
# TABLES

Base = declarative_base()


class Config(Base):
    __tablename__ = 'config'

    id = Column(Integer, primary_key=True)
    login_token = Column(String)


# -----------------------------------------------------------------------------
# FUNCTIONS

def getLoginToken():
    config = session.query(Config).first()

    if config:
        return config.login_token


def setLoginToken(token):
    config = session.query(Config).first()

    if not config:
        config = Config()

    config.login_token = token

    session.add(config)
    session.commit()


# -----------------------------------------------------------------------------
# ENGINE

if not os.path.exists(config.DB_FOLDER):
    os.makedirs(config.DB_FOLDER)

path = os.path.join(config.DB_FOLDER, 'main.db')
engine = create_engine('sqlite:///{}'.format(path))

Base.metadata.create_all(engine)


# -----------------------------------------------------------------------------
# SESSION

session = sessionmaker(bind=engine)()
