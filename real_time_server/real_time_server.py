# -----------------------------------------------------------------------------
# IMPORTS

# Standard library imports
import datetime
import json
import os
import re
import sys

# Should import and install before importing Twisted
import qt4reactor
qt4reactor.install()

# Related third party imports
from twisted.internet import reactor
from twisted.web.resource import Resource
from twisted.web.server import Site

# Local application/library specific imports
from utils import config
from utils import excepthook
import models

# -----------------------------------------------------------------------------
# CLASSES


class Server(Resource):

    isLeaf = True

    def __init__(self, processJsons):
        self.processJsons = processJsons

    def render_GET(self, request):
        try:
            project, error = getRunningProject('test', request.uri)

            if error:
                request.setResponseCode(403)
                return error
            else:
                return "Real time server #{} is accepting requests".format(project.id)

        except:
            request.setResponseCode(500)
            return handleException()

    def render_POST(self, request):
        try:
            project, error = getRunningProject('post', request.uri)

            if error:
                request.setResponseCode(403)
                return error
            else:
                rows = json.loads(request.content.read())
                message = processPost(project, rows)
                self.processJsons(project)
                return message

        except:
            request.setResponseCode(500)
            return handleException()


# -----------------------------------------------------------------------------
# FUNCTIONS

def getRunningProject(name, uri):
    id = getProjectId(name, uri)

    if id is None:
        project = None
        error = "Invalid URL"
    else:

        project = models.getProjectById(id)
        if not project:
            error = "There is no real time server with ID #{}".format(id)
        elif not project.in_progress:
            error = "Real time server #{} is stopped".format(id)
        else:
            error = None

    return project, error


def getProjectId(name, uri):
    pattern = re.compile('/(\d+)/' + name + '/?$', re.IGNORECASE)
    match = re.search(pattern, uri)

    if match:
        return int(match.group(1))


def handleException():
    excepthook.excepthook(sys.exc_type, sys.exc_value, sys.exc_traceback)
    return "Server error: {}".format(sys.exc_value)


def processPost(project, rows):
    folder = os.path.join(config.DB_FOLDER, str(project.id), 'posts')
    if not os.path.exists(folder):
        os.makedirs(folder)

    project.posts_folder = folder
    project.save()

    now = '{:%y%m%d_%H%M%S_%f}'.format(datetime.datetime.now())
    path = os.path.join(folder, now + '.json')

    with open(path, 'w') as f:
        json.dump(rows, f)

    return "{} row(s) processed".format(len(rows))


def startServer(processJsons):
    server = Server(processJsons)
    reactor.listenTCP(config.PORT, Site(server))


# -----------------------------------------------------------------------------
# MAIN
