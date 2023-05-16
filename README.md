Gopher Vision is a collection of Python utilities for interacting with the go4-23c/e data format.

### Installation
```
git clone
cd gopher-vision
pip install -r requirements.txt
```

Gopher Vision 

### Usage

`go4v.py` contains core functionality like escaping & unescaping packets, generating random data, and parsing packets. `go4v` expects `gophercan-lib` to be in the same parent directory so that it can find the specified GopherCAN configuration.

`to-csv.py` extracts packets from a `.gdat` file and outputs them in CSV format.

```
python to-csv.py [FILENAME].gdat
```

`tx.py` generates random data packets from a specified list of parameter IDs and sends them to a connected XBee module. This is useful for testing the telemetry system.

```
python tx.py
```

`rx.py` reads data from a connected XBee, parses packets, calculates statistics, and stores the most recent datapoint for each GopherCAN parameter. The `SAVE_HISTORY` flag optionally writes all data received to a log file.

```
python rx.py
```

`gui.py` provides a GUI with plots available for each GopherCAN parameter. `rx.py` is run in another thread to provide samples. Together, these two scripts form a live telemetry system.

```
python gui.py
```