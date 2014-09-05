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
from utils import config

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
    visible = Column(Boolean)

    name = Column(String)
    form_name = Column(String)
    type_name = Column(String)
    project_token = Column(String)
    validation = Column(String)

    path = Column(String)
    delimiter = Column(String)

    chunks_folder = Column(String)
    posts_folder = Column(String)
    errors_file = Column(String)

    status = Column(String)
    in_progress = Column(Boolean)
    stopped = Column(Boolean)
    idle = Column(Boolean)
    error = Column(String)

    validated = Column(Boolean)
    paused = Column(Boolean)
    uploaded = Column(Boolean)

    records_valid = Column(Integer)
    records_invalid = Column(Integer)
    records_uploaded = Column(Integer)

    def save(self):
        session.add(self)
        session.commit()

        for listener in project_listeners:
            listener(self)

    @property
    def full_status(self):
        if self.paused:
            return self.status + " paused"
        elif self.error:
            return self.status + " failed with error: {}".format(self.error)
        else:
            return self.status

    @property
    def ready_status(self):
        if self.type_name == 'File':
            if not self.validated:
                return "Ready for validation"
            else:
                return "Ready for uploading"
        else:
            return "Ready to serve"

    @property
    def server_url(self):
        return '{}/{}/post'.format(config.URL, self.id)


class Chunk(Base):
    __tablename__ = 'chunk'

    id = Column(Integer, primary_key=True)

    project_id = Column(Integer, ForeignKey('project.id'))
    project = relationship("Project", backref=backref('chunks', order_by=id))

    json_path = Column(String)
    path = Column(String)

    records_valid = Column(Integer)
    records_invalid = Column(Integer)
    uploaded = Column(Boolean)

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


def addProject(name, form_name, type_name, path, project_token, delimiter, validation):
    project = Project(
        name=name,
        form_name=form_name,
        type_name=type_name,
        path=path,
        project_token=project_token,
        delimiter=delimiter or ',',
        validation=validation,
        records_valid=0,
        records_invalid=0,
        visible=True,
        in_progress=False,
        stopped=False,
        idle=False,
        validated=False,
        paused=False,
        uploaded=False
        )
    project.status = project.ready_status
    project.save()

    folder = os.path.join(config.DB_FOLDER, str(project.id), 'chunks')
    if not os.path.exists(folder):
        os.makedirs(folder)

    project.chunks_folder = folder
    project.save()

    return project.id


def getProjectById(project_id):
    return session.query(Project).filter(Project.id==project_id).first()


def getProjects(visible):
    return session.query(Project).filter(Project.visible==visible).all()


def getRunningProjects():
    projects = session.query(Project).filter(Project.in_progress==True).all()
    projects += session.query(Project).filter(Project.paused==True).all()
    return projects


def hasInProgress():
    files = session.query(Project).filter(
        Project.type_name=='File',
        Project.in_progress==True
        ).all()

    servers = session.query(Project).filter(
        Project.type_name=='Server',
        Project.in_progress==True, Project.idle==False
        ).all()

    return bool(files or servers)


# -----------------------------------------------------------------------------
# FUNCTIONS - CHUNKS


def addChunk(project, path, json_path, records_valid, records_invalid):
    chunk = Chunk(
        project=project,
        json_path=json_path,
        path=path,
        records_valid=records_valid,
        records_invalid=records_invalid,
        uploaded=False
        )
    chunk.save()


def updateRecordsCount(project):
    valid = session.query(func.sum(Chunk.records_valid)).filter(Chunk.project==project).scalar()
    invalid = session.query(func.sum(Chunk.records_invalid)).filter(Chunk.project==project).scalar()

    project.records_valid = valid
    project.records_invalid = invalid
    project.save()


def getChunksToUpload(project):
    query = session.query(Chunk).filter(Chunk.project==project, Chunk.uploaded==False)
    return query.all()


def getUploadedCount(project):
    query = session.query(func.sum(Chunk.records_valid))
    query = query.filter(Chunk.project==project, Chunk.uploaded==True)
    return query.scalar()


def removeBrokenChunks(project, json_path):
    session.query(Chunk).filter(Chunk.project==project, Chunk.json_path==json_path).delete()
    session.commit()


def removeChunks(project):
    session.query(Chunk).filter(Chunk.project==project).delete()
    session.commit()


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
