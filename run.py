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
            title = "Your version of the application is outdated"
            text = "Please download the <a href='{}'>recent version {}</a>".format(
                result['url'],
                result['new_version']
                )
            QtGui.QMessageBox.critical(None, title, text)
            self.close()
        else:
            self.checkToken()

    def checkToken(self):
        token = models.getLoginToken()
        result = post('check_login_token', {'token': token})
        error = result.get('error')

        if error == 'Invalid token':
            login_window.show()
            self.close()

        elif error:
            QtGui.QMessageBox.critical(None, 'Error message from the server', error)
            self.close()

        else:
            main_window.show()
            self.close()


class LoginWindow(QtGui.QMainWindow):

    def __init__(self):
        super(LoginWindow, self).__init__()
        self.buildWidgets()

    def buildWidgets(self):
        self.setWindowTitle(u"Please log in")

        label_name = QtGui.QLabel(u"Username:")
        label_name.setAlignment(QtCore.Qt.AlignRight)

        label_pass = QtGui.QLabel(u"Password:")
        label_pass.setAlignment(QtCore.Qt.AlignRight)

        self.edit_name = QtGui.QLineEdit()

        self.edit_pass = QtGui.QLineEdit()
        self.edit_pass.setEchoMode(QtGui.QLineEdit.Password)

        button = QtGui.QPushButton("&Log in")
        button.clicked.connect(self.logIn)

        grid = QtGui.QGridLayout()
        grid.addWidget(label_name, 0, 0)
        grid.addWidget(label_pass, 1, 0)
        grid.addWidget(self.edit_name, 0, 1)
        grid.addWidget(self.edit_pass, 1, 1)
        grid.addWidget(button, 2, 1)

        central = QtGui.QWidget()
        central.setLayout(grid)
        self.setCentralWidget(central)

    def logIn(self):
        username = self.edit_name.text()
        password = self.edit_pass.text()
        result = post('log_in', {'username': username, 'password': password})

        if result.get('error') == 'Invalid username or password':
            text = 'Invalid username or password'
            QtGui.QMessageBox.critical(None, text, text)

        elif result.get('error'):
            QtGui.QMessageBox.critical(None, 'Error message from the server', result['error'])
            self.close()

        else:
            models.setLoginToken(result['token'])
            connecting_window.show()
            QtCore.QTimer().singleShot(500, connecting_window.checkToken)
            self.close()


class MainWindow(QtGui.QMainWindow):

    def __init__(self):
        super(MainWindow, self).__init__()
        self.buildWidgets()

    def buildWidgets(self):
        self.setWindowTitle(u"Cool name for the app")
        self.setSizeAndPosition(800, 600)

    def setSizeAndPosition(self, width, height):
        desktop = QtGui.QApplication.desktop()
        screen = desktop.screenGeometry(desktop.primaryScreen())
        rect = QtCore.QRect(0, 0, width, height)

        if screen.width() < width:
            rect.setWidth(screen.width())
        if screen.height() < 600:
            rect.setHeight(screen.height())

        rect.moveCenter(screen.center())
        self.setGeometry(rect)


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
login_window = LoginWindow()
connecting_window = ConnectingWindow()

connecting_window.show()

sys.exit(app.exec_())
