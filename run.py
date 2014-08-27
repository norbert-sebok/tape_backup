# -----------------------------------------------------------------------------
# IMPORTS

# Standard library imports
import json
import os
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
        result = post("check_version", {"version": config.VERSION})

        if "new_version" in result:
            title = "Your version of the application is outdated"
            text = "Please download the <a href='{}'>recent version {}</a>".format(
                result["url"],
                result["new_version"]
                )
            QtGui.QMessageBox.critical(None, title, text)
            self.close()
        else:
            self.checkToken()

    def checkToken(self):
        token = models.getLoginToken()
        result = post("check_login_token", {"token": token})
        error = result.get("error")

        if error == "Invalid token":
            login_window.show()
            self.close()

        elif error:
            QtGui.QMessageBox.critical(None, "Error message from the server", error)
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

        button = createButton("&Log in", "gtk-dialog-authentication.png", self.logIn)

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
        result = post("log_in", {"username": username, "password": password})

        if result.get("error") == "Invalid username or password":
            text = "Invalid username or password"
            QtGui.QMessageBox.critical(None, text, text)

        elif result.get("error"):
            QtGui.QMessageBox.critical(None, "Error message from the server", result["error"])
            self.close()

        else:
            models.setLoginToken(result["token"])
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

        self.createTable()
        self.createButtons()

        layout = QtGui.QVBoxLayout()
        layout.addWidget(self.view)
        layout.addLayout(self.buttons_layout)

        central = QtGui.QWidget()
        central.setLayout(layout)
        self.setCentralWidget(central)

    def setSizeAndPosition(self, width, height):
        desktop = QtGui.QApplication.desktop()
        screen = desktop.screenGeometry(desktop.primaryScreen())

        width = min(screen.width(), width)
        height = min(screen.height(), height)
        rect = QtCore.QRect(0, 0, width, height)

        rect.moveCenter(screen.center())
        self.setGeometry(rect)

    def createTable(self):
        self.model = TableModel()

        self.view = QtGui.QTableView()
        self.view.setModel(self.model)
        self.view.resizeColumnsToContents()

    def reloadTable(self, project_id=None):
        self.model.loadRows()
        self.model.reset()

        if project_id:
            self.selectById(project_id)

    def selectById(self, id):
        for count, row in enumerate(self.model.rows):
            if row[0] == id:
                index = self.model.createIndex(count, 0)
                self.view.setCurrentIndex(index)

    def createButtons(self):
        button_add = createButton(u"&Add new file", "list-add.png", self.onNewFileClicked)

        self.buttons_layout = QtGui.QHBoxLayout()
        self.buttons_layout.addWidget(button_add)
        self.buttons_layout.addStretch()

    def onNewFileClicked(self):
        self.w = NewFileWindow()
        self.w.show()


class TableModel(QtCore.QAbstractTableModel):

    header = ["ID", "Project Name", "Form name", "Type", "Status", "Project token", "Path"]

    def __init__(self):
        super(TableModel, self).__init__()
        self.loadRows()

    def loadRows(self):
        self.rows = [
            (p.id, p.name, p.form_name, p.type_name, "..", p.project_token, p.path)
            for p in models.getProjects()
            ]

    def rowCount(self, parent):
        return len(self.rows)

    def columnCount(self, parent):
        return len(self.header)

    def data(self, index, role):
        if not index.isValid():
            return None
        elif role != QtCore.Qt.DisplayRole:
            return None
        else:
            return self.rows[index.row()][index.column()]

    def headerData(self, col, orientation, role):
        if orientation == QtCore.Qt.Horizontal and role == QtCore.Qt.DisplayRole:
            return self.header[col]


class NewFileWindow(QtGui.QMainWindow):

    def __init__(self):
        super(NewFileWindow, self).__init__()
        self.buildWidgets()

    def buildWidgets(self):
        self.setWindowTitle(u"New file")

        label_name = QtGui.QLabel(u"Project name:")
        label_name.setAlignment(QtCore.Qt.AlignRight)

        label_form = QtGui.QLabel(u"Form name:")
        label_form.setAlignment(QtCore.Qt.AlignRight)

        label_file = QtGui.QLabel(u"File:")
        label_file.setAlignment(QtCore.Qt.AlignRight)

        self.edit_name = QtGui.QLineEdit()

        self.drop_form = QtGui.QComboBox()
        for name in config.FORM_NAMES:
            self.drop_form.addItem(name)

        button = createButton("&Create", "list-add.png", self.onCreate)
        self.button_file = createButton("...", None, self.selectFile)
        self.path = None

        grid = QtGui.QGridLayout()
        grid.addWidget(label_name, 0, 0)
        grid.addWidget(label_form, 1, 0)
        grid.addWidget(label_file, 2, 0)
        grid.addWidget(self.edit_name, 0, 1)
        grid.addWidget(self.drop_form, 1, 1)
        grid.addWidget(self.button_file, 2, 1)
        grid.addWidget(button, 3, 1)

        central = QtGui.QWidget()
        central.setLayout(grid)
        self.setCentralWidget(central)

    def selectFile(self):
        title = u"Which file would you like to upload?"
        default = QtCore.QDir().homePath()
        path, _ = QtGui.QFileDialog().getOpenFileName(None, title, default)

        if path:
            self.button_file.setText(os.path.basename(path))
            self.path = path

    def onCreate(self):
        name = self.edit_name.text()
        form_name = self.drop_form.currentText()
        type_name = "Real time"

        checks = [
            (name, "Please set the project name", self.edit_name),
            (form_name, "Please select the form name", self.drop_form),
            (self.path, "Please select a file", self.button_file)
            ]

        for value, text, widget in checks:
            if not value:
                QtGui.QMessageBox.critical(None, "Missing data", text)
                widget.setFocus()
                return

        project_token = getProjectToken(name, form_name, type_name)
        project_id = models.addProject(name, form_name, type_name, self.path, project_token)
        main_window.reloadTable(project_id)

        self.close()


# -----------------------------------------------------------------------------
# FUNCTIONS - GUI

def createButton(text, icon_name, func):
    button = QtGui.QPushButton(text)
    button.connect(button, QtCore.SIGNAL("clicked()"), func)

    if icon_name:
        icon = QtGui.QIcon(os.path.join("images", icon_name))
        button.setIcon(icon)

    return button


# -----------------------------------------------------------------------------
# FUNCTIONS - API


def getProjectToken(name, form_name, type_name):
    result = post("get_project_token", {"name": name, "form_name": form_name, "type_name": type_name})

    if result.get("error"):
        QtGui.QMessageBox.critical(None, "Error message from the server", result["error"])

    else:
        return result["project_token"]


def post(route, data):
    try:
        return post_core(route, data)

    except Exception, e:
        QtGui.QMessageBox.critical(None, "Error happened", str(e))
        raise


def post_core(route, data):
    url = "{}/{}".format(config.API_URL, route)
    json_data = json.dumps(data)
    headers = {"content-type": "application/json"}

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
