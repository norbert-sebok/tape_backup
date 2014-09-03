# -----------------------------------------------------------------------------
# IMPORTS

# Standard library imports
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

    def render_GET(self, request):
        try:
            id, error = getRunningProjectId('test', request.uri)

            if error:
                request.setResponseCode(403)
                return error
            else:
                return "Real time server #{} is accepting requests".format(id)

        except:
            request.setResponseCode(500)
            return handleException()

    def render_POST(self, request):
        print 'post'
        return 'ok'


# -----------------------------------------------------------------------------
# FUNCTIONS

def getRunningProjectId(name, uri):
    id = getProjectId(name, uri)

    if id is None:
        error = "Invalid URL"
    else:
        project = models.getProjectById(id)
        if not project:
            error = "There is no real time server with ID #{}".format(id)
        elif not project.serving:
            error = "Real time server #{} is stopped".format(id)
        else:
            error = None

    return id, error


def getProjectId(name, uri):
    pattern = re.compile('/(\d+)/' + name + '/?$', re.IGNORECASE)
    match = re.search(pattern, uri)

    if match:
        return int(match.group(1))


def handleException():
    excepthook.excepthook(sys.exc_type, sys.exc_value, sys.exc_traceback)
    return "Server error: {}".format(sys.exc_value)


def startServer():
    reactor.listenTCP(config.PORT, Site(Server()))


# -----------------------------------------------------------------------------
# MAIN
