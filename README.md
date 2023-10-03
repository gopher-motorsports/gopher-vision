GopherVision is a collection of Python (3.11) utilities for interacting with Gopher Motorsports data.

## Installation
```
git clone https://github.com/gopher-motorsports/gopher-vision.git
cd gopher-vision
pipenv install
```

## Usage
```
pipenv run python go4v.py
```

`go4v.py` opens an interactive console with several commands available:
```
>>> help()
-------------  -----------------------------------------------------------------------------
load(path)     load a .gdat, .ld, or GopherCAN config (.yaml) into memory and parse the data
info()         print basic info on currently loaded data
info_config()  print detailed info on a loaded GopherCAN config
info_gdat()    print detailed info on a loaded .gdat file
info_ld()      print detailed info on a loaded .ld file
plot_gdat(id)  plot .gdat channel data
plot_ld(name)  plot .ld channel data
convert(path)  convert the currently loaded .gdat to a .ld at "path"
help()         print available commands
exit()         exit the console
-------------  -----------------------------------------------------------------------------
```

**WARNING:** Backslashes in path arguments must be escaped. Use `load("configs\\go4-23c.yaml")` instead of `load("configs\go4-23c.yaml")`.

Using a console enables users to load data once, then inspect and plot channels at will without running a script again / reloading.