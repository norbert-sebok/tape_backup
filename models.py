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

    status = Column(String)
    in_progress = Column(Boolean)
    validated = Column(Boolean)
    chunked = Column(Boolean)
    paused = Column(Boolean)

    records_validated = Column(Integer)
    records_invalid = Column(Integer)
    records_chunked = Column(Integer)
    records_uploaded = Column(Integer)

    def save(self):
        session.add(self)
        session.commit()

        for func in project_listeners:
            func(self)


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
        project_token=project_token,
        status="Ready for validation"
        )

    project.save()

    return project.id


def getProjects():
    return session.query(Project).all()


def setValidation(project, validation):
    project.validation = validation
    project.save()


def setStatus(project, status):
    project.status = status
    project.save()


def setInProgress(project, in_progress):
    project.in_progress = in_progress
    project.save()


def setValidated(project):
    project.validated = True
    project.status = "Validated"
    project.save()


def clearBrokenProjectsOnAppStart():
    projects = session.query(Project).filter(Project.in_progress==True).all()
    projects += session.query(Project).filter(Project.paused==True).all()

    for project in projects:
        project.in_progress = False
        project.paused = False
        project.status = "Broken"
        project.save()


def stopProject(project):
    project.in_progress = False
    project.status += " stopped"
    project.save()


def pauseProject(project):
    project.paused = True
    project.status += " paused"
    project.save()


def continueProject(project):
    project.paused = False
    project.save()


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
# MAIN

session = sessionmaker(bind=engine)()
project_listeners = []

clearBrokenProjectsOnAppStart()
