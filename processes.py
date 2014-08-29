# -----------------------------------------------------------------------------
# IMPORTS

# Standard library imports
import calendar
import csv
import datetime
import json
import os
import zipfile

# Related third party imports

# Local application/library specific imports
import config
import models

# -----------------------------------------------------------------------------
# CLASSES - PROCESS MANAGER


class ProcessManager(object):
    
    def __init__(self, processEvents):
        self.processEvents = processEvents
        self.processes = []
        self.running = False

    def addProcess(self, process):
        self.processes.append(process)

    def stopAllProcesses(self):
        for process in self.processes:
            process.stopProcess()

    def stopProcess(self, project):
        for process in self.processes:
            if process.project == project:
                process.stopProcess()

    def pauseProcess(self, project):
        for process in self.processes:
            if process.project == project:
                process.pauseProcess()

    def continueProcess(self, project):
        for process in self.processes:
            if process.project == project:
                process.continueProcess()

    def runProcesses(self):
        if not self.running:
            self.running = True
            self.runProcessesCore()
            self.running = False

    def runProcessesCore(self):
        while True:
            for p in self.processes:
                if not p.paused:
                    p.runOneStep()

            self.processEvents()

            self.processes = [p for p in self.processes if p.running]
            if not self.processes:
                break

            live_processes = [p for p in self.processes if not p.paused]
            if not live_processes:
                break


# -----------------------------------------------------------------------------
# PROCESS

class Process(object):

    def __init__(self, project):
        self.project = project
        self.project.in_progress = True
        self.project.save()

        self.running = True
        self.paused = False
        self.finished = False

        self.generator = self.runProcess()

    def runOneStep(self):
        try:
            self.generator.next()
        except StopIteration:
            self.project.in_progress = False
            self.project.save()

    def runProcess(self):
        pass

    def stopProcess(self):
        self.running = False
        self.project.in_progress = False
        self.project.paused = False
        self.project.status += " stopped"
        self.project.save()

    def pauseProcess(self):
        self.paused = True
        self.project.paused = True
        self.project.status += " paused"
        self.project.save()

    def continueProcess(self):
        self.paused = False
        self.project.paused = False
        self.project.save()

    def markAsFinished(self):
        self.finished = True
        self.running = False

        self.project.in_progress = False
        self.project.save()


# -----------------------------------------------------------------------------
# VALIDATION PROCESS


class ValidationProcess(Process):

    def runProcess(self):
        self.validators = getValidators(self.project)
        errors = 0

        self.project.delimiter = ','
        self.project.save()

        with open(self.project.path) as f:
            reader = csv.reader(f, delimiter=str(self.project.delimiter))

            for count, row in enumerate(reader):
                if not validateRow(self.validators, row):
                    errors += 1
                    self.saveToErrorsFile(row)

                if (count + 1) % 1000 == 0:
                    self.calcStatus(count, errors)

                if count % 100 == 0:
                    yield

        self.calcStatus(count, errors)
        self.markAsFinished()

        self.project.validated = True
        self.project.status = "Ready for chunking"
        self.project.save()

    def calcStatus(self, count, errors):
        self.project.status = "Validating..."
        self.project.records_validated = count + 1 - errors
        self.project.records_invalid = errors
        self.project.save()

    def saveToErrorsFile(self, row):
        folder = os.path.join(config.DB_FOLDER, str(self.project.id))
        if not os.path.exists(folder):
            os.makedirs(folder)

        self.project.errors_file = os.path.join(folder, "validating_errors.csv")
        self.project.save()

        with open(self.project.errors_file, "a") as f:
            line = self.project.delimiter.join(row)
            f.write(line + '\n')


def getValidators(project):
    d = {
        'number': validateNumber,
        'text': validateText,
        'datetimestamp': validateStamp
        }

    return [d[v] for v in project.validation.split(',')]


def validateRow(validators, row):
    for validator, value in zip(validators, row):
        if not validator(value):
            return False

    return True

def validateNumber(value):
    try:
        float(value)
        return True
    except:
        return False


def validateStamp(value):
    try:
        datetime.datetime.strptime(value, '%Y-%m-%d')
        return True
    except:
        return False


def validateText(value):
    return True


# -----------------------------------------------------------------------------
# SPLIT TO CHUNKS PROCESS


class SplitToChunksProcess(Process):

    rows_per_chunk = 400

    def __init__(self, project):
        self.converters = getConverters(project)

        super(SplitToChunksProcess, self).__init__(project)
        self.createFolder()

    def createFolder(self):
        folder = os.path.join(config.DB_FOLDER, str(self.project.id), 'chunks')
        if not os.path.exists(folder):
            os.makedirs(folder)

        self.project.chunks_folder = folder
        self.project.save()

    def runProcess(self):
        self.chunk_count = 0
        self.row_count = 0

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

        self.project.chunked = True
        self.project.status = "Ready for uploading"
        self.project.save()

    def processChunk(self, chunk):
        name = "{:09d}.json.zip".format(self.chunk_count)
        path = os.path.join(self.project.chunks_folder, name)

        data = list(self.convertedRows(chunk))
        json_str = json.dumps(data)
        with zipfile.ZipFile(path, mode='w') as z:
            z.writestr('chunk.csv', json_str)

        self.chunk_count += 1
        self.row_count += len(data)

        chunk = models.Chunk(project=self.project, path=path)
        chunk.save()

    def convertedRows(self, rows):
        for row in rows:
            try:
                yield [func(value) for func, value in zip(self.converters, row)]
            except:
                pass

    def calcStatus(self):
        self.project.status = "Chunking..."
        self.project.records_chunked = self.row_count
        self.project.save()


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

        for chunk in self.project.chunks:
            self.uploadChunk(chunk)
            self.calcStatus()
            yield

        self.calcStatus()
        self.markAsFinished()

        self.project.uploaded = True
        self.project.status = "Uploaded"
        self.project.save()

    def uploadChunk(self, chunk):
        with zipfile.ZipFile(chunk.path, "r") as z:
            data = z.read("chunk.csv")
            rows = json.loads(data)

        result, error = self.post("upload_rows", {
            "login_token": models.getLoginToken(),
            "project_token": self.project.project_token,
            "rows": rows
            })

        if not error:
            self.count += len(rows)
            chunk.upload_id = result['upload_id']
            chunk.save()

    def calcStatus(self):
        self.project.status = "Uploading..."
        self.project.records_uploaded = self.count
        self.project.save()


# -----------------------------------------------------------------------------
# MAIN
