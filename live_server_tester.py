# -----------------------------------------------------------------------------
# IMPORTS

# Standard library imports

# Related third party imports
import requests

# Local application/library specific imports

# -----------------------------------------------------------------------------
# FUNCTIONS

# -----------------------------------------------------------------------------
# MAIN

r = requests.get('http://localhost:8880')
print r.status_code
print r.content
