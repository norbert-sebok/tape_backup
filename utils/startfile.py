# -----------------------------------------------------------------------------
# IMPORTS

# Standard library imports
import subprocess
import sys

# Related third party imports

# Local application/library specific imports

# -----------------------------------------------------------------------------
# FUNCTIONS


def startfile(path):
    if sys.platform=='win32':
        os.startfile(path)

    elif sys.platform=='darwin':
        subprocess.Popen(['open', path])

    else:
        subprocess.Popen(['xdg-open', path])


# -----------------------------------------------------------------------------
# MAIN
