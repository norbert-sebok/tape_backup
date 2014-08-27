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

    def runProcess(self, process):
        self.processes.append(process)

        if not self.running:
            self.running = True
            self.runProcesses()
            self.running = False

    def runProcesses(self):
        while True:
            for p in self.processes:
                p.runOneStep()

            self.processEvents()

            self.processes = [p for p in self.processes if p.isRunning()]
            if not self.processes:
                break


# -----------------------------------------------------------------------------
# VALIDATION PROCESS


class ValidationProcess(object):

    def __init__(self, project, updateGui):
        self.project = project
        self.updateGui = updateGui

        self.validators = getValidators(project)
        self.errors = {count: 0 for count, _ in enumerate(self.validators)}

        models.setInProgress(project, True)
        self.generator = self.runProcess()

    def isRunning(self):
        return self.project.in_progress

    def runOneStep(self):
        try:
            self.generator.next()
        except StopIteration:
            models.setInProgress(project, False)

    def runProcess(self):
        with open(self.project.path) as f:
            reader = csv.reader(f, delimiter=',', quotechar='"')

            for count, row in enumerate(reader):
                validateRow(self.validators, row, self.errors)
                self.updateStatus(count + 1)
                yield

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
