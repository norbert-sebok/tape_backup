# -----------------------------------------------------------------------------
# IMPORTS

# Standard library imports
import json
import os
import time
import sys

# Related third party imports
from PySide import QtCore, QtGui
import requests

# Local application/library specific imports
import config
import excepthook
import models
import processes
import startfile

# -----------------------------------------------------------------------------
# WINDOWS


class ConnectingWindow(QtGui.QMainWindow):

    def __init__(self):
        super(ConnectingWindow, self).__init__()
        self.buildWidgets()

        QtCore.QTimer().singleShot(500, self.checkVersion)

    def buildWidgets(self):
        setTitleAndIcon(self, "Cool name for the app", 'python.png')

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
        result, error = post('check_version', {'version': config.VERSION})

        if error:
            self.close()

        elif 'new_version' in result:
            title = "Your version of the application is outdated"
            text = "Please download the <a href='{}'>recent version {}</a>".format(
                result['url'],
                result['new_version']
                )
            QtGui.QMessageBox.critical(None, title, text)
            self.close()

        else:
            main_window.show()
            self.close()


class LoginWindow(QtGui.QDialog):

    def __init__(self):
        super(LoginWindow, self).__init__()
        self.buildWidgets()

    def buildWidgets(self):
        setTitleAndIcon(self, "Please log in", 'gtk-dialog-authentication.png')
        self.setMinimumWidth(200)

        label_name = QtGui.QLabel(u"Username:")
        label_name.setAlignment(int(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignRight))

        label_pass = QtGui.QLabel(u"Password:")
        label_pass.setAlignment(int(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignRight))

        self.edit_name = QtGui.QLineEdit()

        self.edit_pass = QtGui.QLineEdit()
        self.edit_pass.setEchoMode(QtGui.QLineEdit.Password)

        cancel_button = createButton("Cancel", 'gtk-cancel.png', self.close)
        login_button = createButton("&Log in", 'gtk-dialog-authentication.png', self.logIn)
        login_button.setDefault(True)

        grid = QtGui.QGridLayout()
        grid.addWidget(label_name, 0, 0)
        grid.addWidget(label_pass, 1, 0)
        grid.addWidget(self.edit_name, 0, 1)
        grid.addWidget(self.edit_pass, 1, 1)

        hbox = QtGui.QHBoxLayout()
        hbox.addWidget(cancel_button)
        hbox.addStretch()
        hbox.addWidget(login_button)

        vbox = QtGui.QVBoxLayout()
        vbox.addLayout(grid)
        vbox.addWidget(getHorizontalLine())
        vbox.addLayout(hbox)

        self.setLayout(vbox)

    def logIn(self):
        username = self.edit_name.text()
        password = self.edit_pass.text()
        result, error = post('log_in', {'username': username, 'password': password})

        if error == "Invalid username or password":
            pass

        elif error:
            self.close()

        else:
            models.setLoginToken(result['token'])
            self.close()


class MainWindow(QtGui.QMainWindow):

    def __init__(self):
        super(MainWindow, self).__init__()
        self.buildWidgets()
        models.project_listeners.append(self.updateRow)

    def closeEvent(self, event):
        if models.hasInProgress():
            title = "There are running processes"
            text = "Would you like to stop all running processes?"

            if choosedYes(self, title, text):
                manager.stopAllProcesses()
                event.accept()
            else:
                event.ignore()

        else:
            event.accept()

    def buildWidgets(self):
        setTitleAndIcon(self, "Cool name for the app", 'python.png')
        self.setSizeAndPosition(900, 600)

        self.createButtons()
        self.createTable()

        layout = QtGui.QVBoxLayout()
        layout.addLayout(self.buttons_top)
        layout.addWidget(self.view)
        layout.addLayout(self.buttons_bottom)

        central = QtGui.QWidget()
        central.setLayout(layout)
        self.setCentralWidget(central)

        self.view.setFocus()

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
        self.setColumnWidths()

        self.view.setSelectionBehavior(self.view.SelectRows)
        self.view.setSelectionMode(self.view.SingleSelection)
        self.view.selectRow(0)

        self.view.connect(
            self.view.selectionModel(),
            QtCore.SIGNAL('currentChanged(const QModelIndex &, const QModelIndex &)'),
            self.enableDisableButtons)
        self.enableDisableButtons()

    def setColumnWidths(self):
        self.view.resizeColumnsToContents()
        self.view.setColumnWidth(4, 300)

    def reloadTable(self, project_id=None):
        if not project_id:
            project = self.getCurrentProject()
            if project:
                project_id = project.id

        self.model.loadRows()
        self.model.reset()
        self.setColumnWidths()

        if project_id:
            self.selectById(project_id)

        if not self.getCurrentProject():
            self.selectFirst()

        self.enableDisableButtons()

    def selectById(self, id):
        count = self.getCountById(id)

        if count is not None:
            index = self.model.createIndex(count, 0)
            self.view.setCurrentIndex(index)

    def selectFirst(self):
        if self.model.rows:
            index = self.model.createIndex(0, 0)
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
        self.button_add = createButton(u"&Add new file", 'list-add.png', self.onNewFileClicked)
        self.button_hide = createButton(u"&Hide", 'edit-copy.png', self.onHideClicked)

        self.button_show = createButton(u"Show hi&dden projects", 'edit-copy-purple.png', self.onShowClicked)
        self.button_show.setCheckable(True)

        self.button_valid = createButton(u"&Validate and split", 'accessories.png', self.onValidateClicked)
        self.button_upload = createButton(u"&Upload", 'internet.png', self.onUploadClicked)
        self.button_open = createButton(u"&Open invalid rows", 'table.png', self.onOpenClicked)
        self.button_continue = createButton(u"&Continue", 'media-start.png', self.onContinueClicked)
        self.button_pause = createButton(u"&Pause", 'media-pause.png', self.onPauseClicked)
        self.button_stop = createButton(u"&Stop", 'media-stop.png', self.onStopClicked)

        self.buttons_top = QtGui.QHBoxLayout()
        self.buttons_top.addWidget(self.button_add)
        self.buttons_top.addSpacing(12)
        self.buttons_top.addWidget(self.button_hide)
        self.buttons_top.addWidget(self.button_show)
        self.buttons_top.addStretch()

        self.buttons_bottom = QtGui.QHBoxLayout()
        self.buttons_bottom.addWidget(self.button_valid)
        self.buttons_bottom.addWidget(self.button_upload)
        self.buttons_bottom.addSpacing(12)
        self.buttons_bottom.addWidget(self.button_open)
        self.buttons_bottom.addSpacing(12)
        self.buttons_bottom.addWidget(self.button_pause)
        self.buttons_bottom.addWidget(self.button_continue)
        self.buttons_bottom.addWidget(self.button_stop)
        self.buttons_bottom.addStretch()

    def enableDisableButtons(self):
        p = self.getCurrentProject()

        if p:
            self.button_hide.setEnabled(bool(p))
            self.button_valid.setEnabled(bool(not p.in_progress and not p.validated))
            self.button_upload.setEnabled(bool(not p.in_progress and p.validated and not p.uploaded))
            self.button_open.setEnabled(bool(p.errors_file))
            self.button_continue.setEnabled(bool(p.paused))
            self.button_pause.setEnabled(bool(p.in_progress and not p.paused))
            self.button_stop.setEnabled(bool(p.in_progress))
        else:
            self.button_hide.setEnabled(False)
            self.button_valid.setEnabled(False)
            self.button_upload.setEnabled(False)
            self.button_open.setEnabled(False)
            self.button_continue.setEnabled(False)
            self.button_pause.setEnabled(False)
            self.button_stop.setEnabled(False)

    def onNewFileClicked(self):
        self.view.setFocus()

        result, error = post('get_form_names', {})

        if not error:
            form_names = result['form_names']
            window = NewFileWindow(form_names)
            window.exec_()

    def onHideClicked(self):
        self.view.setFocus()

        project = self.getCurrentProject()
        if not project:
            return

        if project.visible:
            title, text = "Hide", "Hide the selected project?"
        else:
            title, text = "Show", "Set the selected project visible?"
        
        if choosedYes(self, title, text):
            project.visible = not project.visible
            project.save()
            self.reloadTable()

    def onShowClicked(self):
        self.view.setFocus()

        if self.button_show.isChecked():
            text = "&Show"
            visible = False
        else:
            text = "&Hide"
            visible = True

        self.button_hide.setText(text)
        self.model.visible = visible
        self.reloadTable()

    def onValidateClicked(self):
        self.view.setFocus()

        project = self.getCurrentProject()
        if not project:
            return

        result, error = post('get_validations', {'form_name': project.form_name})

        if not error:
            project.validation = result['validation']
            project.save()

            process = processes.ValidationAndSplitProcess(project)
            manager.addProcess(process)
            QtCore.QTimer().singleShot(10, manager.runProcesses)

            self.enableDisableButtons()

    def onUploadClicked(self):
        self.view.setFocus()

        project = self.getCurrentProject()

        process = processes.UploadProcess(project, post)
        manager.addProcess(process)
        QtCore.QTimer().singleShot(10, manager.runProcesses)

        self.enableDisableButtons()

    def onOpenClicked(self):
        self.view.setFocus()

        project = self.getCurrentProject()
        startfile.startfile(project.errors_file)

    def onContinueClicked(self):
        self.view.setFocus()

        project = self.getCurrentProject()
        manager.continueProcess(project)
        QtCore.QTimer().singleShot(10, manager.runProcesses)
        self.reloadTable()

    def onPauseClicked(self):
        self.view.setFocus()

        project = self.getCurrentProject()
        manager.pauseProcess(project)
        self.reloadTable()

    def onStopClicked(self):
        self.view.setFocus()

        project = self.getCurrentProject()
        manager.stopProcess(project)
        self.reloadTable()

    def updateRow(self, project):
        count = self.getCountById(project.id)

        if count is not None:
            row = self.model.loadRow(project)
            self.model.rows[count] = row

            for index, _ in enumerate(row):
                self.model.dataChanged.emit(count, index)

        self.enableDisableButtons()
        self.setColumnWidths()


class TableModel(QtCore.QAbstractTableModel):

    header = [
        "ID", "Project Name", "Form name", "Type", "Status",
        "Invalid", "Validated", "Chunked", "Uploaded", "Path"
        ]

    def __init__(self):
        super(TableModel, self).__init__()
        self.visible = True
        self.loadRows()

    def loadRows(self):
        self.rows = [self.loadRow(p) for p in models.getProjects(self.visible)]

    def loadRow(self, p):
        invalid = "{:,}".format(p.records_invalid or 0)
        validated = "{:,}".format(p.records_validated or 0)
        chunked = "{:,}".format(p.records_chunked or 0)
        uploaded = "{:,}".format(p.records_uploaded or 0)

        return [
            p.id, p.name, p.form_name, p.type_name, p.full_status,
            invalid, validated, chunked, uploaded, p.path, p
            ]

    def rowCount(self, parent):
        return len(self.rows)

    def columnCount(self, parent):
        return len(self.header)

    def data(self, index, role):
        if not index.isValid():
            return None

        elif role == QtCore.Qt.TextAlignmentRole:
            col = index.column()
            title = self.header[col]

            if title in ("Validated", "Invalid", "Chunked", "Uploaded"):
                return int(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignRight)
            else:
                return int(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft)

        elif role == QtCore.Qt.DisplayRole:
            return self.rows[index.row()][index.column()]

    def headerData(self, col, orientation, role):
        if orientation == QtCore.Qt.Horizontal and role == QtCore.Qt.DisplayRole:
            return self.header[col]


class NewFileWindow(QtGui.QDialog):

    def __init__(self, form_names):
        super(NewFileWindow, self).__init__()
        self.form_names = form_names
        self.buildWidgets()

    def buildWidgets(self):
        setTitleAndIcon(self, "Add new file", 'list-add.png')
        self.setMinimumWidth(300)

        label_name = QtGui.QLabel(u"Project name:")
        label_name.setAlignment(int(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignRight))

        label_form = QtGui.QLabel(u"Form name:")
        label_form.setAlignment(int(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignRight))

        label_file = QtGui.QLabel(u"File:")
        label_file.setAlignment(int(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignRight))

        self.edit_name = QtGui.QLineEdit()

        self.drop_form = QtGui.QComboBox()
        for name in self.form_names:
            self.drop_form.addItem(name)

        cancel_button = createButton("Cancel", 'gtk-cancel.png', self.close)
        create_button = createButton("&Add new file", 'list-add.png', self.onCreate)
        create_button.setDefault(True)

        self.button_file = createButton("...", None, self.selectFile)
        self.path = None

        grid = QtGui.QGridLayout()
        grid.addWidget(label_name, 0, 0)
        grid.addWidget(label_form, 1, 0)
        grid.addWidget(label_file, 2, 0)
        grid.addWidget(self.edit_name, 0, 1)
        grid.addWidget(self.drop_form, 1, 1)
        grid.addWidget(self.button_file, 2, 1)

        hbox = QtGui.QHBoxLayout()
        hbox.addWidget(cancel_button)
        hbox.addStretch()
        hbox.addWidget(create_button)

        vbox = QtGui.QVBoxLayout()
        vbox.addLayout(grid)
        vbox.addWidget(getHorizontalLine())
        vbox.addLayout(hbox)

        self.setLayout(vbox)

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

        data = {'name': name, 'form_name': form_name, 'type_name': type_name}
        result, error = post('get_project_token', data)

        if not error:
            project_token = result['project_token']
            project_id = models.addProject(name, form_name, type_name, self.path, project_token)
            main_window.reloadTable(project_id)
            self.close()


# -----------------------------------------------------------------------------
# FUNCTIONS - GUI


def choosedYes(window, title, text):
    yes = QtGui.QMessageBox.Yes
    no = QtGui.QMessageBox.No

    answer = QtGui.QMessageBox.question(window, title, text, yes, no)
    return answer == yes

def createButton(text, icon_name, func):
    button = QtGui.QPushButton(text)
    button.connect(button, QtCore.SIGNAL('clicked()'), func)

    if icon_name:
        button.setIcon(getIcon(icon_name))

    return button


def getHorizontalLine():
    line = QtGui.QFrame()
    line.setFrameShape(QtGui.QFrame.HLine)
    line.setFrameShadow(QtGui.QFrame.Sunken)
    return line


def getIcon(icon_name):
    return QtGui.QIcon(os.path.join('images', icon_name))


def setTitleAndIcon(window, title, icon_name):
    window.setWindowTitle(title)
    window.setWindowIcon(getIcon(icon_name))


# -----------------------------------------------------------------------------
# FUNCTIONS - API


def post(route, data, count=0):
    data['login_token'] = models.getLoginToken()

    try:
        result = post_core(route, data)
        error = result.get('error')

        if error == "Invalid login token":
            login_window = LoginWindow()
            login_window.exec_()
        elif error:
            QtGui.QMessageBox.critical(None, "Error happened", error)

        return result, error

    except requests.ConnectionError:
        if count < 2:
            time.sleep(0.1)
            return post(route, data, count+1)
        else:
            error = "The server is unreachable"
            QtGui.QMessageBox.critical(None, "Error happened", error)
            return None, error

    except Exception, e:
        QtGui.QMessageBox.critical(None, "Error happened", str(e))
        raise


def post_core(route, data):
    url = "{}/{}".format(config.API_URL, route)
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
manager = processes.ProcessManager(app.processEvents)

main_window = MainWindow()
connecting_window = ConnectingWindow()
connecting_window.show()

sys.exit(app.exec_())
