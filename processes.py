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

    def __init__(self, processEvents):
        self.processEvents = processEvents
        self.processes = {}
        self.running = False

    def addProcess(self, project, process):
        self.processes[project.id] = process

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
        return [p for p in self.processes.values() if not p.project.paused]

# -----------------------------------------------------------------------------
# PROCESS


class Process(object):

    def __init__(self, project):
        self.project = project
        self.project.in_progress = True
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

    rows_per_chunk = 400

    def runProcess(self):
        self.createFolder()
        self.converters = getConverters(self.project)

        self.chunk_count = 0
        self.records_validated = 0
        self.records_invalid = 0

        with open(self.project.path) as f:
            reader = csv.reader(f, delimiter=str(self.project.delimiter))

            chunk = []
            for row in reader:
                chunk.append(row)

                if len(chunk) == self.rows_per_chunk:
                    self.processChunk(chunk)
                    self.calcStatus()
                    chunk = []
                    yield

            if chunk:
                self.processChunk(chunk)

        self.calcStatus()
        self.markAsFinished()

        self.project.validated = True
        self.project.status = "Ready for uploading"
        self.project.save()

    def processChunk(self, chunk):
        name = '{:09d}.json.zip'.format(self.chunk_count)
        path = os.path.join(self.project.chunks_folder, name)

        data = list(self.convertedRows(chunk))

        json_str = json.dumps(data)
        with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as z:
            z.writestr('chunk.csv', json_str)

        self.chunk_count += 1
        self.records_validated += len(data)

        models.addOrUpdateChunk(self.project, path, len(data))

    def convertedRows(self, rows):
        for row in rows:
            try:
                yield [func(value) for func, value in zip(self.converters, row)]
            except:
                self.records_invalid += 1
                self.saveToErrorsFile(row)

    def createFolder(self):
        folder = os.path.join(config.DB_FOLDER, str(self.project.id), 'chunks')
        if not os.path.exists(folder):
            os.makedirs(folder)

        self.project.chunks_folder = folder
        self.project.save()

    def calcStatus(self):
        self.project.status = "Validating and splitting..."
        self.project.error = None
        self.project.records_chunked = self.records_validated
        self.project.records_validated = self.records_validated
        self.project.records_invalid = self.records_invalid
        self.project.save()

    def saveToErrorsFile(self, row):
        folder = os.path.join(config.DB_FOLDER, str(self.project.id))
        if not os.path.exists(folder):
            os.makedirs(folder)

        self.project.errors_file = os.path.join(folder, 'validating_errors.csv')
        self.project.save()

        with open(self.project.errors_file, 'a') as f:
            line = self.project.delimiter.join(row)
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
        self.count = 0
        self.project.status = "Uploading..."
        self.calcStatus()

        for chunk in self.project.chunks:
            if not chunk.upload_id:
                self.uploadChunk(chunk)
                yield

        chunks = self.getChunksToReupload()
        if not chunks:
            return

        count = 0
        while chunks:
            count += 1
            self.project.status = "Checking uploads ({}. cycle)...".format(count)
            self.calcStatus()

            for chunk in chunks:
                self.uploadChunk(chunk)
                yield

            if count > 4:
                self.stopProcess("Too many upload checking cycle")
                return

            chunks = self.getChunksToReupload()

        self.calcStatus()
        self.markAsFinished()

        self.project.uploaded = True
        self.project.status = "Done"
        self.project.save()

    def uploadChunk(self, chunk):
        with zipfile.ZipFile(chunk.path, 'r') as z:
            data = z.read('chunk.csv')
            rows = json.loads(data)

        result, error = self.post('upload_rows', {
            'login_token': models.getLoginToken(),
            'project_token': self.project.project_token,
            'rows': rows
            })

        if error:
            self.stopProcess(error)

        else:
            self.count += len(rows)
            chunk.uploaded = True
            chunk.upload_id = result['upload_id']
            chunk.save()
            self.calcStatus()

    def getChunksToReupload(self):
        result, error = self.post('get_upload_ids', {
            'login_token': models.getLoginToken(),
            'project_token': self.project.project_token
            })

        if error:
            self.stopProcess(error)

        else:
            upload_ids = set(result['upload_ids'])
            return [c for c in self.project.chunks if c.upload_id not in upload_ids]

    def calcStatus(self):
        self.project.error = None
        self.project.records_uploaded = models.getUploadedCount(self.project)
        self.project.save()


# -----------------------------------------------------------------------------
# SERVER PROCESS


class ServerProcess(Process):

    def __init__(self, project, post):
        self.post = post

        super(ServerProcess, self).__init__(project)

    def runProcess(self):
        self.project.status = "Running..."
        self.project.serving = True
        self.project.save()

        for i in range(10):
            print i
            yield

        self.project.status = "Running... (idle)"
        self.project.save()

    def stopProcess(self, error=None):
        self.project.status = "Stopped"
        self.project.serving = False
        super(ServerProcess, self).stopProcess(error)


# -----------------------------------------------------------------------------
# MAIN
