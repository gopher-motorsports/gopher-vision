**GopherVision** is a collection of Python utilities for interacting with Gopher Motorsports data.

## Quickstart

_Just want the GUI?_ Vist the [Releases](https://github.com/gopher-motorsports/gopher-vision/releases) page to download the latest version of the desktop app. You can find `GopherVision.exe` under the "Assets" dropdown.

![](https://private-user-images.githubusercontent.com/69396515/287429527-bf7b86d8-db46-4286-b7c2-0f86df608253.png?jwt=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJnaXRodWIuY29tIiwiYXVkIjoicmF3LmdpdGh1YnVzZXJjb250ZW50LmNvbSIsImtleSI6ImtleTUiLCJleHAiOjE3MTI4NzM4NDAsIm5iZiI6MTcxMjg3MzU0MCwicGF0aCI6Ii82OTM5NjUxNS8yODc0Mjk1MjctYmY3Yjg2ZDgtZGI0Ni00Mjg2LWI3YzItMGY4NmRmNjA4MjUzLnBuZz9YLUFtei1BbGdvcml0aG09QVdTNC1ITUFDLVNIQTI1NiZYLUFtei1DcmVkZW50aWFsPUFLSUFWQ09EWUxTQTUzUFFLNFpBJTJGMjAyNDA0MTElMkZ1cy1lYXN0LTElMkZzMyUyRmF3czRfcmVxdWVzdCZYLUFtei1EYXRlPTIwMjQwNDExVDIyMTIyMFomWC1BbXotRXhwaXJlcz0zMDAmWC1BbXotU2lnbmF0dXJlPTQ1YTk0YWE2ZTVlMTlhOTRiYjdlNDY2MDZmYmZkOTQwMWM0NjFjNGNmMGUxYTkwYTRhZjc4MWE2NDMxMjBlZGEmWC1BbXotU2lnbmVkSGVhZGVycz1ob3N0JmFjdG9yX2lkPTAma2V5X2lkPTAmcmVwb19pZD0wIn0.5_NtaI5UQ1h94K1ngdF5beuQ2rhNf5P5YXO9IgzcOxs)

## Installation
1. Install [Python 3.8.10](https://www.python.org/downloads/) or newer
2. Clone the project and install dependencies:
```
git clone https://github.com/gopher-motorsports/gopher-vision.git
cd gopher-vision
pip install -r requirements.txt
```

*Optionally*, you might want to create a virtual environment for dependencies using [venv](https://docs.python.org/3/library/venv.html).

## Usage
### GUI
**Option 1:** [Download](https://github.com/gopher-motorsports/gopher-vision/releases) and run `GopherVision.exe`

**Option 2:** `python gui.py`

### CLI
Start the GopherVision console:
```console
$ python cli.py

Welcome to GopherVision. Enter ? to list commands.

(GopherVision) ?

Documented commands (type help <topic>):
========================================
convert  exit  help  info  load  plot  query


(GopherVision)
```

Get help with a command:
```console
(GopherVision) help convert
convert a .gdat file (or folder of .gdat files) to .ld

        convert [GOPHERCAN CONFIG NAME] [PATH TO .gdat]
        e.g. "convert go4-23c.yaml statefair.gdat"

        convert [GOPHERCAN CONFIG NAME] [PATH TO FOLDER]
        e.g. "convert go4-23c.yaml data/"
```

Convert a `.gdat` file to `.ld`:
```console
(GopherVision) convert go4-23c.yaml data/mock_endurance.gdat
loaded GopherCAN config: ..\gophercan-lib\network_autogen\configs\go4-23c.yaml
loading data\mock_endurance.gdat ...
...
writing to "data\mock_endurance.ld"... (0.5s)
```

Inspect the data in a `.gdat` file:
```console
(GopherVision) load go4-23c.yaml data/cooling_test.gdat
loaded GopherCAN config: ..\gophercan-lib\network_autogen\configs\go4-23c.yaml
loading data\cooling_test.gdat ...
...
created 117 channels
loaded in (26.08s)

(GopherVision) info gdat
path: data\cooling_test.gdat
t0: Tue Oct 22 14:07:06 2052
      ╷                              ╷       ╷            ╷          ╷        ╷           ╷                      ╷                     ╷              ╷              ╷       ╷        ╷         ╷
  id  │ name                         │ unit  │ type       │ n_points │ t_min  │ t_max     │ v_min                │ v_max               │ frequency_hz │ sample_count │ shift │ scalar │ divisor │ offset  
╶─────┼──────────────────────────────┼───────┼────────────┼──────────┼────────┼───────────┼──────────────────────┼─────────────────────┼──────────────┼──────────────┼───────┼────────┼─────────┼────────╴
  1   │ Engine RPM                   │ rpm   │ UNSIGNED16 │ 225396   │ 354.0  │ 1131077.0 │ 0.0                  │ 3367.0              │ 200          │ 226215       │ 4     │ 297    │ 1250    │ 0
  2   │ Engine Temp                  │ C     │ FLOATING   │ 56445    │ 356.0  │ 1131072.0 │ 9.100000381469727    │ 73.70000457763672   │ 50           │ 56553        │ 6     │ 80     │ 737     │ 0
  3   │ Eng Oil Pres                 │ kPa   │ FLOATING   │ 56434    │ 356.0  │ 1131072.0 │ 101.30000305175781   │ 581.0               │ 50           │ 56553        │ 5     │ 80     │ 581     │ 0
  4   │ Eng Oil Temp                 │ C     │ FLOATING   │ 56427    │ 356.0  │ 1131072.0 │ 8.699999809265137    │ 46.60000228881836   │ 50           │ 56553        │ 6     │ 40     │ 233     │ 0
...
```

Exit the console:
```console
(GopherVision) exit
```

Use `?` and `help` for information on available commands.

## Contributing

Build `GopherVision.exe`:
```
pyinstaller gui.py --onefile --distpath ./ --name GopherVision
```
