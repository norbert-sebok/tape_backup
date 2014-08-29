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

    def __init__(self, project):
        self.validators = getValidators(project)
        self.errors = {count: 0 for count, _ in enumerate(self.validators)}

        super(ValidationProcess, self).__init__(project)

    def runProcess(self):
        with open(self.project.path) as f:
            reader = csv.reader(f, delimiter=',', quotechar='"')

            for count, row in enumerate(reader):
                validateRow(self.validators, row, self.errors)

                if (count + 1) % 1000 == 0:
                    self.calcStatus(count)

                if count % 100 == 0:
                    yield

        self.calcStatus(count)
        self.markAsFinished()

        invalid = sum(self.errors.values())
        if not invalid:
            self.project.validated = True
            self.project.status = "Ready for chunking"
            self.project.save()

    def calcStatus(self, count):
        invalid = sum(self.errors.values())
        valid = count + 1 - invalid

        self.project.status = "Validating..."
        self.project.records_validated = valid
        self.project.records_invalid = invalid
        self.project.save()


def getValidators(project):
    d = {
        'number': validateNumber,
        'text': validateText,
        'datetimestamp': validateStamp
        }

    return [d[v] for v in project.validation.split(',')]


def validateRow(validators, row, errors):
    for count, (validator, value) in enumerate(zip(validators, row)):
        if not validator(value):
            errors[count] += 1


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

    def runProcess(self):
        self.chunk_count = 0

        with open(self.project.path) as f:
            reader = csv.reader(f, delimiter=',', quotechar='"')

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
        folder = os.path.join(config.CHUNK_FOLDER, str(self.project.id))
        if not os.path.exists(folder):
            os.makedirs(folder)

        name = "{:09d}.json".format(self.chunk_count)
        path = os.path.join(folder, name+'.zip')

        data = self.convertedRows(chunk)
        json_str = json.dumps(data)
        with zipfile.ZipFile(path, mode='w') as z:
            z.writestr(name, json_str)

        self.chunk_count += 1

    def convertedRows(self, rows):
        return [self.convertedRow(row) for row in rows]

    def convertedRow(self, row):
        return [func(value) for func, value in zip(self.converters, row)]

    def calcStatus(self):
        self.project.status = "Chunking..."
        self.project.records_chunked = self.chunk_count * self.rows_per_chunk
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
# MAIN
