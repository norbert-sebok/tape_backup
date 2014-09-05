# -----------------------------------------------------------------------------
# IMPORTS

# Standard library imports
import collections
import json
import random
import uuid

# Related third party imports
import flask

# Local application/library specific imports

# -----------------------------------------------------------------------------
# DATA

VALID_LOGIN_TOKEN = "A VALID LOGIN TOKEN"

# -----------------------------------------------------------------------------
# ROUTES

app = flask.Flask(__name__)


@app.route('/check_version', methods=['POST'])
def check_version():
    version = flask.request.json['version']

    if version == '2.3':
        result = {}
    else:
        result = {
            'new_version': '2.3',
            'url': 'http://download_site.com/installer_v2.3'
            }

    return json.dumps(result)


@app.route('/log_in', methods=['POST'])
def log_in():
    username = flask.request.json['username']
    password = flask.request.json['password']

    if username == "somebody" and password == "secret":
        result = {'token': VALID_LOGIN_TOKEN}
    else:
        result = {'error': "Invalid username or password"}

    return json.dumps(result)


@app.route('/check_login_token', methods=['POST'])
def check_login_token():
    login_token = flask.request.json['login_token']

    if isValidLoginToken(login_token):
        result = {}
    else:
        result = {'error': "Invalid login token"}

    return json.dumps(result)


@app.route('/get_project_token', methods=['POST'])
def get_project_token():
    login_token = flask.request.json['login_token']
    name = flask.request.json['name']
    form_name = flask.request.json['form_name']
    type_name = flask.request.json['type_name']

    if isValidLoginToken(login_token):
        project_token = str(uuid.uuid4())
        result = {'project_token': project_token}
    else:
        result = {'error': "Invalid login token"}

    return json.dumps(result)


@app.route('/get_form_names', methods=['POST'])
def get_form_names():
    login_token = flask.request.json['login_token']

    if isValidLoginToken(login_token):
        result = {'form_names': ["Type alpha", "Type beta", "Type gamma", "Delta"]}
    else:
        result = {'error': "Invalid login token"}

    return json.dumps(result)


@app.route('/get_validations', methods=['POST'])
def get_validations():
    login_token = flask.request.json['login_token']
    form_name = flask.request.json['form_name']

    if isValidLoginToken(login_token):
        result = {'validation': 'number,number,text,datetimestamp'}
    else:
        result = {'error': "Invalid login token"}

    return json.dumps(result)


@app.route('/upload_rows', methods=['POST'])
def upload_rows():
    login_token = flask.request.json['login_token']
    project_token = flask.request.json['project_token']
    chunk_id = flask.request.json['chunk_id']
    rows = flask.request.json['rows']

    if isValidLoginToken(login_token):
        if chunk_id in chunk_ids:
            result = {'error': "Already uploaded"}
        else:
            chunk_ids.add(chunk_id)
            result = {'chunk_id': chunk_id}

    else:
        result = {'error': "Invalid login token"}

    return json.dumps(result)


# -----------------------------------------------------------------------------
# FUNCTIONS


def isValidLoginToken(login_token):
    return login_token == VALID_LOGIN_TOKEN


# -----------------------------------------------------------------------------
# MAIN

chunk_ids = set()

if __name__ == '__main__':
    app.run(debug=True)
