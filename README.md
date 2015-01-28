### Tape backup ###

A cross platform desktop application for backing up huge amounts of data stored
currently in tape drives. User can create as many processes as she/he wants. 
Every process uploads in parallel into an external API. The API is implemented
elsewhere, here is only a fake server exists for testing purposes.

The inputs are CSV files. APIs can be started too which can be feed by other
applications (Salesforce for example).

Input data is validated, chunked, converted to JSON and uploaded in chunks.

![Main window](/screenshot/main.png?raw=true "Main window")

### Installation on Ubuntu ###

Prerequisites for PySide:

```
sudo apt-get install build-essential cmake libqt4-dev libphonon-dev python2.7-dev libxml2-dev libxslt1-dev qtmobility-dev
```

Python packages used by the fake server:

```
pip install flask
```

By the GUI:

```
pip install pyside
pip install requests
pip install sqlalchemy
pip install twisted

```

### Run ###

The server can be started by:
```
python run_fake_server.py

```

The GUI:
```
python run.py

```
