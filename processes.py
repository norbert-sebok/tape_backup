# -----------------------------------------------------------------------------
# IMPORTS

# Standard library imports
import csv
import datetime

# Related third party imports

# Local application/library specific imports
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
                self.runProcesses()

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
# VALIDATION PROCESS


class ValidationProcess(object):

    def __init__(self, project, updateGui):
        self.project = project
        self.updateGui = updateGui

        self.validators = getValidators(project)
        self.errors = {count: 0 for count, _ in enumerate(self.validators)}

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
        with open(self.project.path) as f:
            reader = csv.reader(f, delimiter=',', quotechar='"')

            for count, row in enumerate(reader):
                validateRow(self.validators, row, self.errors)
                self.updateStatus(count + 1)
                yield

        self.finished = True
        self.running = False

    def updateStatus(self, count):
        if count % 1000 == 0:
            invalid = sum(self.errors.values())
            valid = count - invalid
            status = "Validating rows: {:,} valid / {:,} invalid".format(valid, invalid)

            models.setStatus(self.project, status)
            self.updateGui(self.project, status)


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
# MAIN
