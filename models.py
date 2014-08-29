# -----------------------------------------------------------------------------
# IMPORTS

# Standard library imports
import os

# Related third party imports
from sqlalchemy import create_engine, func
from sqlalchemy import Boolean, Column, ForeignKey, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import backref, relationship, sessionmaker

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
    project_token = Column(String)
    validation = Column(String)

    path = Column(String)
    delimiter = Column(String)

    chunks_folder = Column(String)
    errors_file = Column(String)

    status = Column(String)
    in_progress = Column(Boolean)
    validated = Column(Boolean)
    chunked = Column(Boolean)
    paused = Column(Boolean)
    uploaded = Column(Boolean)

    records_validated = Column(Integer)
    records_invalid = Column(Integer)
    records_chunked = Column(Integer)
    records_uploaded = Column(Integer)

    def save(self):
        session.add(self)
        session.commit()

        for func in project_listeners:
            func(self)


class Chunk(Base):
    __tablename__ = 'chunk'

    id = Column(Integer, primary_key=True)

    project_id = Column(Integer, ForeignKey('project.id'))
    project = relationship("Project", backref=backref('chunks', order_by=id))

    path = Column(String)
    rows = Column(Integer)

    uploaded = Column(Boolean)
    upload_id = Column(String)

    def save(self):
        session.add(self)
        session.commit()


# -----------------------------------------------------------------------------
# FUNCTIONS - CONFIG


def getLoginToken():
    config = session.query(Config).first()

    if config:
        return config.login_token


def setLoginToken(value):
    config = session.query(Config).first() or Config()
    config.login_token = value

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


def clearBrokenProjectsOnAppStart():
    projects = session.query(Project).filter(Project.in_progress==True).all()
    projects += session.query(Project).filter(Project.paused==True).all()

    for project in projects:
        project.in_progress = False
        project.paused = False
        project.status = "Broken"
        project.save()


def hasInProgress():
    return bool(session.query(Project).filter(Project.in_progress==True).all())


# -----------------------------------------------------------------------------
# FUNCTIONS - CHUNKS


def getUploadedCount(project):
    query = session.query(func.sum(Chunk.rows))
    query = query.filter(Chunk.project==project, Chunk.uploaded==True)
    return query.scalar()


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
