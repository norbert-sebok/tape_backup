# -----------------------------------------------------------------------------
# IMPORTS

# Standard library imports
import csv
import datetime
import functools
import json
import os
import sys

# Related third party imports
from PySide import QtCore, QtGui
import requests

# Local application/library specific imports
import config
import models
import processes

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
        result, _ = post("check_version", {"version": config.VERSION})

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
        login_token = models.getLoginToken()

        _, error = post("check_login_token", {"login_token": login_token})

        if not error:
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
        result, error = post("log_in", {"username": username, "password": password})

        if error == "Invalid username or password":
            text = "Invalid username or password"
            QtGui.QMessageBox.critical(None, text, text)

        elif error:
            QtGui.QMessageBox.critical(None, "Error message from the server", error)
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

    def closeEvent(self, event):
        if models.hasInProgress():
            title = "There are running processes"
            text = "Would you like to stop all running processes?"
            yes = QtGui.QMessageBox.Yes
            no = QtGui.QMessageBox.No
            answer = QtGui.QMessageBox.question(self, title, text, yes, no)

            if answer == yes:
                manager.stopAllProcesses()
                event.accept()
            else:
                event.ignore()

        else:
            event.accept()

    def buildWidgets(self):
        self.setWindowTitle(u"Cool name for the app")
        self.setSizeAndPosition(800, 600)

        self.createButtons()
        self.createTable()

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

        self.view.connect(
            self.view.selectionModel(),
            QtCore.SIGNAL("currentChanged(const QModelIndex &, const QModelIndex &)"),
            self.enableDisableButtons)
        self.enableDisableButtons()

    def reloadTable(self, project_id=None):
        if not project_id:
            project = self.getCurrentProject()
            if project:
                project_id = project.id

        self.model.loadRows()
        self.model.reset()

        if project_id:
            self.selectById(project_id)

        self.enableDisableButtons()

    def selectById(self, id):
        count = self.getCountById(id)
        if count:
            index = self.model.createIndex(count, 0)
            self.view.setCurrentIndex(index)

    def getCountById(self, id):
        for count, row in enumerate(self.model.rows):
            if row[0] == id:
                return count

    def getCurrentProject(self):
        i = self.view.currentIndex().row()
        if i > -1:
            row = self.model.rows[i]
            project = row[-1]
            return project

    def createButtons(self):
        self.button_add = createButton(u"&Add new file", "list-add.png", self.onNewFileClicked)
        self.button_valid = createButton(u"&Validate", "gtk-apply.png", self.onValidateClicked)
        self.button_split = createButton(u"Split &to chunks", "accessories.png", self.onSplitClicked)
        self.button_continue = createButton(u"&Continue", "media-start.png", self.onContinueClicked)
        self.button_pause = createButton(u"&Pause", "media-pause.png", self.onPauseClicked)
        self.button_stop = createButton(u"&Stop", "media-stop.png", self.onStopClicked)

        self.buttons_layout = QtGui.QHBoxLayout()
        self.buttons_layout.addWidget(self.button_add)
        self.buttons_layout.addSpacing(10)
        self.buttons_layout.addWidget(self.button_valid)
        self.buttons_layout.addWidget(self.button_split)
        self.buttons_layout.addSpacing(10)
        self.buttons_layout.addWidget(self.button_pause)
        self.buttons_layout.addWidget(self.button_continue)
        self.buttons_layout.addWidget(self.button_stop)
        self.buttons_layout.addStretch()

    def enableDisableButtons(self):
        project = self.getCurrentProject()

        exists = bool(project)
        in_progress = bool(project and project.in_progress)
        validated = bool(project and project.validated)
        paused = bool(project and project.paused)

        self.button_valid.setEnabled(exists and not in_progress and not validated)
        self.button_split.setEnabled(validated)
        self.button_continue.setEnabled(paused)
        self.button_pause.setEnabled(in_progress and not paused)
        self.button_stop.setEnabled(in_progress)

    def onNewFileClicked(self):
        login_token = models.getLoginToken()
        result, error = post("get_form_names", {"login_token": login_token})

        if not error:
            form_names = result["form_names"]
            self.w = NewFileWindow(form_names)
            self.w.show()

        self.view.setFocus()

    def onValidateClicked(self):
        project = self.getCurrentProject()
        login_token = models.getLoginToken()
        result, error = post("get_validations", {"login_token": login_token, 'form_name':project.form_name})

        if not error:
            models.setValidation(project, result["validation"])

            process = processes.ValidationProcess(project, self.updateStatus, self.reloadTable)
            manager.addProcess(process)
            QtCore.QTimer().singleShot(10, manager.runProcesses)

            self.enableDisableButtons()

        self.view.setFocus()

    def onSplitClicked(self):
        project = self.getCurrentProject()

        process = processes.SplitToChunksProcess(project, self.updateStatus, self.reloadTable)
        manager.addProcess(process)
        QtCore.QTimer().singleShot(10, manager.runProcesses)

        self.enableDisableButtons()
        self.view.setFocus()

    def onContinueClicked(self):
        project = self.getCurrentProject()
        manager.continueProcess(project)
        QtCore.QTimer().singleShot(10, manager.runProcesses)
        self.reloadTable()
        self.view.setFocus()

    def onPauseClicked(self):
        project = self.getCurrentProject()
        manager.pauseProcess(project)
        self.reloadTable()
        self.view.setFocus()

    def onStopClicked(self):
        project = self.getCurrentProject()
        manager.stopProcess(project)
        self.reloadTable()
        self.view.setFocus()

    def updateStatus(self, project, status):
        count = self.getCountById(project.id)
        if count != None:
            self.model.rows[count][self.model.status_index] = status
            self.model.dataChanged.emit(count, self.model.status_index)


class TableModel(QtCore.QAbstractTableModel):

    header = ["ID", "Project Name", "Form name", "Type", "Status", "Project token", "Path"]
    status_index = 4

    def __init__(self):
        super(TableModel, self).__init__()
        self.loadRows()

    def loadRows(self):
        self.rows = [
            [p.id, p.name, p.form_name, p.type_name, p.status, p.project_token, p.path, p]
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

    def __init__(self, form_names):
        super(NewFileWindow, self).__init__()
        self.form_names = form_names
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
        for name in self.form_names:
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
        type_name = "File"

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

        if project_token:
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
    login_token = models.getLoginToken()
    data = {"login_token": login_token, "name": name, "form_name": form_name, "type_name": type_name}

    result, error = post("get_project_token", data)

    return (None if error else result["project_token"])


def post(route, data):
    try:
        result = post_core(route, data)
        error = result.get("error")

        if error == "Invalid login token":
            login_window.show()

        return result, error

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

manager = processes.ProcessManager(app.processEvents)

connecting_window.show()

sys.exit(app.exec_())
