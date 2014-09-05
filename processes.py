# -----------------------------------------------------------------------------
# IMPORTS

# Standard library imports
import csv
import datetime
import json
import os
import sys
import zipfile

# Related third party imports

# Local application/library specific imports
from utils import config
from utils import excepthook
import models

# -----------------------------------------------------------------------------
# CLASSES - PROCESS MANAGER


class ProcessManager(object):

    def __init__(self, post, processEvents):
        self.post = post
        self.processEvents = processEvents
        self.processes = {}
        self.running = False

    def addProcess(self, project, process):
        self.processes[project.id] = process

    def processJsons(self, project):
        if not project.id in self.processes:
            process = ServerProcess(project, self.post)
            self.addProcess(project, process)

        process = self.processes[project.id]
        process.processJsons()
        self.runProcesses()

    def stopAllProcesses(self):
        for process in self.processes.values():
            process.stopProcess()

    def stopProcess(self, project):
        if project.id in self.processes:
            process = self.processes[project.id]
            process.stopProcess()

    def pauseProcess(self, project):
        if project.id in self.processes:
            process = self.processes[project.id]
            process.pauseProcess()

    def continueProcess(self, project):
        if project.id in self.processes:
            process = self.processes[project.id]
            process.continueProcess()

    def runProcesses(self):
        if not self.running:
            self.running = True
            self.runProcessesCore()
            self.running = False

    def runProcessesCore(self):
        while True:
            for p in self.processes.values():
                if not p.project.paused:
                    p.runOneStep()

            self.processEvents()

            self.processes = {id: p for (id, p) in self.processes.items() if p.project.in_progress}

            if not self.live_processes:
                break

    @property
    def live_processes(self):
        return [p for p in self.processes.values() if not p.project.paused and not p.project.idle]

# -----------------------------------------------------------------------------
# PROCESS


class Process(object):

    def __init__(self, project):
        self.project = project
        self.startProcess()

    def startProcess(self):
        self.project.in_progress = True
        self.project.error = None
        self.project.save()

        self.finished = False
        self.generator = self.runProcess()

    def runOneStep(self):
        try:
            self.generator.next()

        except StopIteration:
            pass

        except Exception, e:
            self.stopProcess(str(e))
            excepthook.excepthook(sys.exc_type, sys.exc_value, sys.exc_traceback)

    def runProcess(self):
        pass

    def stopProcess(self, error=None):
        self.project.status = self.project.ready_status
        self.project.in_progress = False
        self.project.paused = False
        self.project.stopped = True
        self.project.error = error
        self.project.save()

    def pauseProcess(self):
        self.project.paused = True
        self.project.save()

    def continueProcess(self):
        self.project.paused = False
        self.project.save()

    def markAsFinished(self):
        self.finished = True

        self.project.in_progress = False
        self.project.save()


# -----------------------------------------------------------------------------
# VALIDATION PROCESS


class ValidationAndSplitProcess(Process):

    def runProcess(self):
        self.converters = getConverters(self.project)
        self.resetProject()

        with open(self.project.path) as f:
            reader = csv.reader(f, delimiter=str(self.project.delimiter))
            for _ in processRows(self.project, self.converters, reader):
                yield

        self.markAsFinished()

        self.project.validated = True
        self.project.status = self.project.ready_status
        self.project.save()

    def resetProject(self):
        if self.project.errors_file:
            os.remove(self.project.errors_file)
            self.project.errors_file = None

        for name in os.listdir(self.project.chunks_folder):
            path = os.path.join(self.project.chunks_folder, name)
            os.remove(path)

        self.project.status = "Validating and splitting..."
        self.project.records_validated = 0
        self.project.records_invalid = 0
        self.project.save()

        models.removeChunks(self.project)


def processRows(project, converters, rows):
    chunk = []

    for row in rows:
        chunk.append(row)

        if len(chunk) == config.ROWS_PER_CHUNK:
            processChunk(project, converters, chunk)
            chunk = []
            yield

    if chunk:
        processChunk(project, converters, chunk)


def processChunk(project, converters, rows):
    name = '{:%y%m%d_%H%M%S_%f}.json.zip'.format(datetime.datetime.now())
    path = os.path.join(project.chunks_folder, name)

    valid_rows = list(convertedRows(project, converters, rows))

    json_str = json.dumps(valid_rows)
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('chunk.csv', json_str)

    project.status = "Validating and splitting..."
    project.records_validated += len(valid_rows)
    project.records_invalid += len(rows) - len(valid_rows)
    project.save()

    models.addOrUpdateChunk(project, path, len(valid_rows))


def convertedRows(project, converters, rows):
    for row in rows:
        try:
            yield [func(value) for func, value in zip(converters, row)]
        except:
            saveToErrorsFile(project, row)


def saveToErrorsFile(project, row):
    folder = os.path.join(config.DB_FOLDER, str(project.id))
    if not os.path.exists(folder):
        os.makedirs(folder)

    project.errors_file = os.path.join(folder, 'validating_errors.csv')
    project.save()

    with open(project.errors_file, 'a') as f:
        line = project.delimiter.join(row)
        f.write(line + '\n')


def getConverters(project):
    d = {
        'number': convertNumber,
        'text': convertText,
        'datetimestamp': convertStamp
        }

    return [d[v] for v in project.validation.split(',')]


def convertNumber(value):
    return float(value)


def convertStamp(value):
    return datetime.datetime.strptime(value, '%Y-%m-%d').isoformat()


def convertText(value):
    return value


# -----------------------------------------------------------------------------
# UPLOAD PROCESS


class UploadProcess(Process):

    def __init__(self, project, post):
        self.post = post

        super(UploadProcess, self).__init__(project)

    def runProcess(self):
        self.project.status = "Uploading..."
        self.project.save()

        for _ in uploadChunks(self, self.project):
            yield

        self.markAsFinished()
        self.project.uploaded = True
        self.project.status = "Done"
        self.project.save()


def uploadChunks(process, project):
    for chunk in models.getChunksToUpload(project):
        uploadChunk(process, chunk)
        project.records_uploaded = models.getUploadedCount(project)
        project.save()
        yield


def uploadChunk(process, chunk):
    with zipfile.ZipFile(chunk.path, 'r') as z:
        data = z.read('chunk.csv')
        rows = json.loads(data)

    result, error = process.post('upload_rows', {
        'login_token': models.getLoginToken(),
        'project_token': chunk.project.project_token,
        'chunk_id': chunk.id,
        'rows': rows
        })

    if not error or error == "Already uploaded":
        chunk.uploaded = True
        chunk.save()

    else:
        process.stopProcess(error)


# -----------------------------------------------------------------------------
# SERVER PROCESS


class ServerProcess(Process):

    def __init__(self, project, post):
        self.project = project
        self.post = post
        self.converters = getConverters(project)

        super(ServerProcess, self).__init__(project)

    def processJsons(self):
        if self.project.idle:
            self.startProcess()

    def runProcess(self):
        self.project.status = "Running..."
        self.project.idle = False
        self.project.save()

        while True:
            for _ in self.runProcessCore():
                yield

            if not self.getPaths() and not models.getChunksToUpload(self.project):
                break

        self.project.status = "Running... (idle)"
        self.project.idle = True
        self.project.save()

    def runProcessCore(self):
        while True:
            paths = self.getPaths()
            if paths:
                for _ in self.processPaths(paths):
                    yield
            else:
                break

        for _ in uploadChunks(self, self.project):
            yield

    def getPaths(self):
        folder = self.project.posts_folder
        if folder:
            names = sorted(os.listdir(folder))
            paths = [os.path.join(folder, name) for name in names]
            return paths

    def processPaths(self, paths):
        for path in paths:
            with open(path) as f:
                rows = json.load(f)

            str_rows = [[str(v) for v in row] for row in rows]
            for _ in processRows(self.project, self.converters, str_rows):
                yield

            os.remove(path)


# -----------------------------------------------------------------------------
# MAIN
