Gopher Vision is a collection of Python utilities for interacting with the go4-23c/e data format.

### Installation
```
git clone
cd gopher-vision
pip install -r requirements.txt
```

### Usage

`go4v.py` contains core functionality like parsing packets and generating data. `go4v` expects `gophercan-lib` to be in the same parent directory so that it can find the specified GopherCAN configuration.

`plot.py` parses a `.gdat` file, organizes packets into GopherCAN channels, and opens a GUI to view the time-series plots.

```
python plot.py [FILENAME].gdat
```

`to-csv.py` extracts packets from a `.gdat` file and outputs them in CSV format.

```
python to-csv.py [FILENAME].gdat
```

`to-ld.py` converts packet data to a MoTeC `.ld` file for use with i2.

```
python to-ld.py [FILENAME].gdat
```

`tx.py` generates random data packets from a specified list of parameter IDs and sends them to a connected XBee module. This is especially useful for testing the telemetry system.

```
python tx.py
```

`rx.py` reads data from a connected XBee, parses packets, calculates statistics, and stores the most recent datapoint for each GopherCAN parameter. The `SAVE_HISTORY` flag optionally writes all data received to a log file.

```
python rx.py
```

`gui.py` opens a GUI with plots available for each GopherCAN parameter. `rx.py` is run in another thread to provide live telemetry samples.

```
python gui.py
```