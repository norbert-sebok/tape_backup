# -----------------------------------------------------------------------------
# IMPORTS

# Standard library imports
import os

# Related third party imports
from sqlalchemy import create_engine, Boolean, Column, Integer, String
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
    project_token = Column(String)
    validation = Column(String)

    in_progress = Column(Boolean)
    status = Column(String)


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

def addProject(name, form_name, type_name, path, project_token):
    project = Project(
        name=name,
        form_name=form_name,
        type_name=type_name,
        path=path,
        project_token=project_token
        )

    session.add(project)
    session.commit()

    return project.id


def getProjects():
    return session.query(Project).all()


def setValidation(project, validation):
    project.validation = validation
    session.add(project)
    session.commit()


def setStatus(project, status):
    project.status = status
    session.add(project)
    session.commit()


def setInProgress(project, in_progress):
    project.in_progress = in_progress
    session.add(project)
    session.commit()


def stopProject(project):
    project.in_progress = False
    project.status = "Stopped"
    session.add(project)
    session.commit()


def hasInProgress():
    return bool(session.query(Project).filter(Project.in_progress==True).all())


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
