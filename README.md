# Switcheroo Lite

A fork of [nxshot](https://github.com/s1cp/nxshot) that has some improved internals and support for nswdb's titleid format.
As the name suggests, it also serves as a "Light" version of [Switcheroo](https://github.com/Tyler-A/Switcheroo) - another Nintendo Switch Album Manager but with more features

## Usage

This can also be obtained py running the python scripe with the `-h` flag

```text
usage: switcheroo_lite.py [-h] [--version] [-u] [-r] [--no-videos] [--no-screenshots] [-q] FILEPATH

Automatically organize and timestamp your Nintendo Switch screenshots and clips

positional arguments:
  FILEPATH              'Nintendo/Album' folder from your SD card.

optional arguments:
  -h, --help            show this help message and exit
  --version             show program's version number and exit
  -u, --update-cache    Update cached games list via online database. Requires key.txt to be present
  -r, --include-regions
                        Include game region - USA, JPN, etc. - in the folder name
  --no-videos           Do not organize video (.mp4) files
  --no-screenshots      Do not organize image (.jpg) files
  -q, --quiet           Don't print standard out to console
  -c, --copy            Copy files instead of generating hard links
  ```

## How to Use

- Download the repository as a [zip file](https://github.com/dmynerd78/switcheroo-lite/archive/master.zip)
- Download/Ensure [Python 3.6+](https://www.python.org/downloads/) is installed - make sure `export to PATH` is enabled
- Install required libraries with `pip install -r requirements.txt`
- Extract zip folder and run the script via command line `python switcheroo_lite.py [path/to/Nintendo/Album/]`

## Use of `key.txt`

`key.txt` holds a hard coded key which is stored within the Nintendo Switch. It's used for programatically decrypting online titleIDs into screenshot IDs. It's possible to use this program without it - you just can't run `--update-cache`

## How to update game IDs cache without `key.txt`

Open up `gameids.json` (in something other than Notepad). In "progammer terms" this uses the [JSON file format](https://www.w3schools.com/whatis/whatis_json.asp) where each screenshot id maps to a game name. Format is as follows:

```json
"SCREENSHOT_ID": "GAME_NAME",
```

Essentially, you want to add the game as a new line in between the two curly brackets. To do this, take the garbled text at the end of a screenshot/video as the first quoted value; the game name is the second value. For example, if we wanted to add "The Legend of Zelda: Breath of the Wild", we would get `F1C11A22FAEE3B82F21B330E1B786A39` from the end of the screenshot/video filename to be our key. If `gameids.json` already has this game, you can simply update the name that follows `F1C11A22FAEE3B82F21B330E1B786A39`. If `gameids.json` does not contain the game, then we would then add the following line to our `gameids.json` file like so:

```json
"F1C11A22FAEE3B82F21B330E1B786A39": "The Legend of Zelda: Breath of the Wild",
```

Note the comma at the end of the sequence. This is required.  
Also note the program will remove any invalid characters (colon, question mark, etc.) from the final name
