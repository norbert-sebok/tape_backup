# -----------------------------------------------------------------------------
# IMPORTS

# Standard library imports
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

    def __init__(self, project, updateStatus, reloadTable):
        self.project = project
        self.updateStatus = updateStatus
        self.reloadTable = reloadTable

        self.running = True
        self.paused = False
        self.finished = False

        models.setInProgress(project, True)
        self.generator = self.runProcess()

    def stopProcess(self):
        self.running = False
        models.stopProject(self.project)

    def pauseProcess(self):
        self.paused = True
        models.pauseProject(self.project)

    def continueProcess(self):
        self.paused = False
        models.continueProject(self.project)

    def runOneStep(self):
        try:
            self.generator.next()
        except StopIteration:
            models.setInProgress(self.project, False)

    def runProcess(self):
        pass

    def markAsFinished(self):
        models.setInProgress(self.project, False)

        self.finished = True
        self.running = False

        self.reloadTable()


# -----------------------------------------------------------------------------
# VALIDATION PROCESS


class ValidationProcess(Process):

    def __init__(self, project, updateStatus, reloadTable):
        self.validators = getValidators(project)
        self.errors = {count: 0 for count, _ in enumerate(self.validators)}

        super(ValidationProcess, self).__init__(project, updateStatus, reloadTable)

    def runProcess(self):
        with open(self.project.path) as f:
            reader = csv.reader(f, delimiter=',', quotechar='"')

            for count, row in enumerate(reader):
                validateRow(self.validators, row, self.errors)
                self.calcStatus(count + 1)

                if count % 100 == 0:
                    yield

        invalid = sum(self.errors.values())
        if not invalid:
            models.setValidated(self.project)

        self.markAsFinished()

    def calcStatus(self, count):
        if count % 1000 == 0:
            invalid = sum(self.errors.values())
            valid = count - invalid
            status = "Validating rows: {:,} valid / {:,} invalid".format(valid, invalid)

            models.setStatus(self.project, status)
            self.updateStatus(self.project, status)


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

        self.markAsFinished()

    def processChunk(self, chunk):
        folder = os.path.join(config.CHUNK_FOLDER, str(self.project.id))
        if not os.path.exists(folder):
            os.makedirs(folder)

        name = "{:09d}.json".format(self.chunk_count)
        path = os.path.join(folder, name+'.zip')

        data = json.dumps(chunk)
        with zipfile.ZipFile(path, mode='w') as z:
            z.writestr(name, data)

        self.chunk_count += 1

    def calcStatus(self):
        rows = self.chunk_count * self.rows_per_chunk
        status = "Split {:,} chunks for {:,} rows".format(self.chunk_count, rows)

        models.setStatus(self.project, status)
        self.updateStatus(self.project, status)


# -----------------------------------------------------------------------------
# MAIN
