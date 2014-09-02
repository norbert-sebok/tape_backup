# -----------------------------------------------------------------------------
# IMPORTS

# Standard library imports
import datetime
import traceback
import sys

# Related third party imports
from PySide import QtGui

# Local application/library specific imports
import config

# -----------------------------------------------------------------------------
# FUNCTIONS


def excepthook(exc_type, exc_value, exc_traceback):
    now = '{:%y-%m-%d - %H:%M:%S}'.format(datetime.datetime.now())
    lines = traceback.format_exception(exc_type, exc_value, exc_traceback)

    with open('log.log', 'a') as f:
        f.write('{} - Exception:\n'.format(now))
        f.write('\n')
        f.write(''.join(lines))
        f.write('\n')

    if config.DEBUG:
        traceback.print_exception(exc_type, exc_value, exc_traceback)

    QtGui.QMessageBox.critical(None, "Error happened", str(exc_value))


# -----------------------------------------------------------------------------
# MAIN

