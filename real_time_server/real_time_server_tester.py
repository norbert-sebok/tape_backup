# -----------------------------------------------------------------------------
# IMPORTS

# Standard library imports
import json

# Related third party imports
import requests

# Local application/library specific imports

# -----------------------------------------------------------------------------
# FUNCTIONS


def get_test(project_id):
    url = 'http://localhost:8880/{}/test'.format(project_id)
    r = requests.get(url)
    return r.content


def post_data(project_id, rows):
    data = json.dumps(rows)

    url = 'http://localhost:8880/{}/post'.format(project_id)
    r = requests.post(url, data=data)
    return r.content


# -----------------------------------------------------------------------------
# MAIN

rows = [[i, i*10, 'lkjkhj', '2014-04-04'] for i in xrange(10*1000)]

print get_test(2)
print post_data(2, rows)
