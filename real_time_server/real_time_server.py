# -----------------------------------------------------------------------------
# IMPORTS

# Standard library imports

# Has to import and install before importing Twisted
import qt4reactor
qt4reactor.install()

# Related third party imports
from twisted.internet import reactor
from twisted.web.resource import Resource
from twisted.web.server import Site

# Local application/library specific imports

# -----------------------------------------------------------------------------
# CLASSES


class Server(Resource):

    isLeaf = True

    def render_GET(self, request):
        return 'ok'


# -----------------------------------------------------------------------------
# FUNCTIONS

def startServer(port=8880):
    reactor.listenTCP(port, Site(Server()))
    return getURL(port)


def getURL(port):
    return 'http://localhost:{}'.format(port)


# -----------------------------------------------------------------------------
# MAIN
