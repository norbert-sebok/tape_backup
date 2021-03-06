
# The version of the current application
VERSION = '2.3'

# The URL of the API server, including the port
API_URL = 'http://127.0.0.1:5000'

# The port and URL of the embedded real time server
PORT = 8880
URL = 'http://localhost:{}'.format(PORT)

# The path of the logo image
LOGO_PATH = 'images/logo.png'

# The folder of the database and temporary filess
DB_FOLDER = 'db'

# Number of rows in one chunk to be uploaded to the server in one POST call
ROWS_PER_CHUNK = 400

# Debug mode prints exceptions
DEBUG = True
