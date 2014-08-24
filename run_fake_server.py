# -----------------------------------------------------------------------------
# IMPORTS

# Standard library imports
import json

# Related third party imports
import flask

# Local application/library specific imports

# -----------------------------------------------------------------------------
# ROUTES

app = flask.Flask(__name__)


@app.route("/check_login_token", methods=['POST'])
def check_login_token():
    token = flask.request.json['token']

    if token == 'A_VALID_TOKEN':
        result = {}
    else:
        result = {'error': 'Invalid token'}

    return json.dumps(result)


# -----------------------------------------------------------------------------
# MAIN

if __name__ == "__main__":
    app.run(debug=True)
