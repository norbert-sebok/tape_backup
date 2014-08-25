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


class Project(Base):
    __tablename__ = 'project'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    form_name = Column(String)
    type_name = Column(String)
    path = Column(String)


# -----------------------------------------------------------------------------
# FUNCTIONS - CONFIG

def getLoginToken():
    return getConfig('login_token')


def setLoginToken(value):
    return setConfig('login_token', value)


def getConfig(attr):
    config = session.query(Config).first()

    if config:
        return getattr(config, attr)


def setConfig(attr, value):
    config = session.query(Config).first()

    if not config:
        config = Config()

    setattr(config, attr, value)

    session.add(config)
    session.commit()


# -----------------------------------------------------------------------------
# FUNCTIONS - PROJECT

def addProject(name, form_name, type_name, path):
    project = Project(
        name=name,
        form_name=form_name,
        type_name=type_name,
        path=path
        )

    session.add(project)
    session.commit()

    return project.id


def getProjects():
    return session.query(Project).all()


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
