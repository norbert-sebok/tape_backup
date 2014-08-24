# -----------------------------------------------------------------------------
# IMPORTS

# Standard library imports
import json
import sys

# Related third party imports
from PySide import QtCore, QtGui
import requests

# Local application/library specific imports
import config
import models

# -----------------------------------------------------------------------------
# WINDOWS


class ConnectingWindow(QtGui.QMainWindow):

    def __init__(self):
        super(ConnectingWindow, self).__init__()
        self.buildWidgets()

        QtCore.QTimer().singleShot(500, self.checkVersion)

    def buildWidgets(self):
        self.setWindowTitle(u"Cool name for the app")

        pixmap = QtGui.QPixmap(config.LOGO_PATH)
        label = QtGui.QLabel()
        label.setPixmap(pixmap)
        label.setAlignment(QtCore.Qt.AlignCenter)

        label_name = QtGui.QLabel(u"<b><FONT SIZE=5>Company name</b>")
        label_name.setAlignment(QtCore.Qt.AlignCenter)

        label_copy = QtGui.QLabel(u"Copyright info, 2000-2014")
        label_copy.setAlignment(QtCore.Qt.AlignCenter)

        hbox = QtGui.QVBoxLayout()
        hbox.addWidget(label)
        hbox.addWidget(label_name)
        hbox.addWidget(label_copy)

        central = QtGui.QWidget()
        central.setLayout(hbox)
        self.setCentralWidget(central)

    def checkVersion(self):
        result = post('check_version', {'version': config.VERSION})

        if 'new_version' in result:
            showNewVersionDialog(result['new_version'], result['url'])
            self.close()
        else:
            self.checkToken()

    def checkToken(self):
        token = models.getLoginToken()
        result = post('check_login_token', {'token': token})

        if 'error' in result:
            raise Exception(result['error'])
        else:
            main_window.show()
            self.close()


class MainWindow(QtGui.QMainWindow):

    def __init__(self):
        super(MainWindow, self).__init__()
        self.buildWidgets()

    def buildWidgets(self):
        self.setWindowTitle(u"Cool name for the app")


# -----------------------------------------------------------------------------
# FUNCTIONS - DIALOGS

def showNewVersionDialog(new_version, url):
    QtGui.QMessageBox.about(
        None,
        "Your version of the application is outdated",
        "Please download the <a href='{}'>recent version {}</a>".format(
            url, new_version
            )
        )


# -----------------------------------------------------------------------------
# FUNCTIONS - API


def post(route, data):
    url = '{}/{}'.format(config.API_URL, route)
    json_data = json.dumps(data)
    headers = {'content-type': 'application/json'}

    r = requests.post(url, data=json_data, headers=headers)

    if r.status_code == 200:
        return r.json()
    else:
        raise Exception(r.content)


# -----------------------------------------------------------------------------
# MAIN

app = QtGui.QApplication(sys.argv)

main_window = MainWindow()
window = ConnectingWindow()
window.show()

sys.exit(app.exec_())
