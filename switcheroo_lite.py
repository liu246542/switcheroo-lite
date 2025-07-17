import os
import sys
import re
import json
import hashlib
import requests
import time
import html
from pathlib import Path
from datetime import datetime
from shutil import copy
from Crypto.Cipher import AES


PROGRAM_VERSION = 1.1
DECRYPT_KEY_HASH = "24e0dc62a15c11d38b622162ea2b4383"

REGION_CODE = "ar,at,au,be,bg,br,ca,ch,cl,cn,co,cy,cz,de,dk,ee,es,fi,fr,gb,gr,hk,hr,hu,ie,it,jp,kr,lt,lu,lv,mt,mx,nl,no,nz,pe,pl,pt,ro,ru,se,si,sk,us,xx,za,zh"

global logger
logger = print


def no_print(*objects, sep=' ', end='\n', file=sys.stdout, flush=False):
    """
    Stub function used for logger. Used for --quiet flag to prevent printing
    """
    pass


def load_key(filename):
    """
    Load key used for decrypting screenshot ids
    NOTE: Exits program if hash doesn't match DECRYPT_KEY_HASH

    Parameters:
        filename: path to key.txt which contains nintendo special key

    Return: decrypted key
    """
    try:
        with open(filename, "r") as keyfile:
            keystring = keyfile.read(32)
            key = bytes.fromhex(keystring)
            if(hashlib.md5(key).hexdigest() not in DECRYPT_KEY_HASH):
                logger("Key does not match hash! Exiting.")
                sys.exit(1)

        return key

    except FileNotFoundError:
        logger("Decryption key (key.txt) not found!")
    except ValueError:
        logger("Decryption key in key.txt doesn't match hash!")

    sys.exit(1)


def clean_filename(gameid, id_map):
    """
    Get folder name from a given gameid

    Parameters:
        gameid: decrypted titleid used to get game name
        id_map: dictionary generated from get_gameids()
        keep_region: append game region to end of folder name

    Returns: Filesystem safe game name
    """
    if gameid not in id_map:
        return "Unknown"

    keepcharacters = (' ', '.', '_')
    name = id_map[gameid]

    return "".join(c for c in name if c.isalnum() or c in keepcharacters).rstrip()


def decrypt_titleid(key, titleid):
    """
    Descrypt encrypted screenshot id

    Parameters:
        key: magic key
        titleid: id straight from screenshot

    Return: decrypted titleid (what nswdb uses)
    """
    cipher = AES.new(key, AES.MODE_ECB)

    titleidb = bytes.fromhex(titleid)
    titleidb = titleidb[7::-1]
    conversion = titleidb.hex()
    conversion = conversion.ljust(32, "0")
    titleidb = bytes.fromhex(conversion)
    encrypted = cipher.encrypt(titleidb)
    screenshotid = encrypted.hex().upper()

    return screenshotid


def get_gameids(force_update=False):
    """
    Get screenshot ids
    Also has an option of updating gameids.json with new
    games from nswdb.com (does not overwrite previous values)
    UPDATE REQUIRES key.txt TO EXIST

    Parameters:
        force_update: grab new game titleids from nswdb.com
                      REQUIRES key.txt TO EXIST

    Return: Dictionary that maps screenshot ids to filesystem
            unfriendly game names
    """
    game_ids = {}
    logger("Reading gameids.json cache file...")

    try:
        with open("gameids.json", "r", encoding="utf-8") as idfile:
            game_ids = json.load(idfile)
    except (FileNotFoundError, json.decoder.JSONDecodeError):
        print("Error reading gameids.json!")
        if not force_update:
            logger(("Error reading gameids.json! "
                    "Please rerun the program with the --update-cache flag "
                    "and ensure you have key.txt in the same directory as "
                    "the executable."))
            sys.exit()

    if force_update:
        logger("Forcing update of gameids.json...")
        download_dict = update_nswdb(game_ids, REGION_CODE)
        download_dict.update(game_ids)
        return download_dict

    return game_ids


def update_nswdb(old_game_ids, region="us"):
    """
    """
    unix_timestamp = int(time.time())
    payload = {
        "region": region,
        "rating": "0",
        "_": unix_timestamp
    }
    id_map = {}

    key = load_key("key.txt")

    r = requests.get("https://tinfoil.media/Title/ApiJson/", params=payload)
    nswdb_raw = r.json()
    for item in nswdb_raw["data"]:
        temp_id = decrypt_titleid(key, item.get("id"))
        temp_title = item.get("name").strip()
        temp_title = temp_title.replace("\n", "").replace("\t", "")
        temp_title = re.findall(r'<a.*?>(.*?)</a>', temp_title)
        assert len(temp_title) == 1
        id_map.setdefault(temp_id, html.unescape(temp_title[0]))

    id_map.update(old_game_ids)
    with open(f"gameids.json", "w", encoding="utf-8") as idfile:
        json.dump(id_map, idfile, ensure_ascii=False, indent=4, sort_keys=True)
        idfile.flush()
        logger("Successfully updated Game IDs")

    return id_map


def check_folders(filelist, game_ids):
    """
    Main copy function

    Parameters:
        filelist: Path objecct of list of files to transfer
        game_ids: dictionary that maps screenshot ids to
                  filesystem safe game names

    Returns: number of files transferred
    """

    num_transferred = 0
    num_skipped = 0
    length = len(filelist)
    if args.copy:
        copy_strategy = lambda src, dst: copy(src, dst)
    else:
        copy_strategy = lambda src, dst: os.link(src, dst + '/' + os.path.basename(src))

    for mediapath in filelist:
        year = mediapath.stem[0:4]
        month = mediapath.stem[4:6]
        day = mediapath.stem[6:8]
        hour = mediapath.stem[8:10]
        minute = mediapath.stem[10:12]
        second = mediapath.stem[12:14]
        gameid = mediapath.stem[17:]

        try:
            time = datetime(int(year), int(month), int(day), 
                hour=int(hour), minute=int(minute), second=int(second))

        except ValueError:
            logger(f"Invalid filename for media {num_transferred}: {mediapath.stem}")

        # posixtimestamp = time.timestamp()

        outputfolder = args.albumpath.joinpath(
            "Organized", clean_filename(gameid, game_ids))

        # TODO Use better output name
        outputfolder.mkdir(parents=True, exist_ok=True)
        if args.overwrite or not os.path.exists(outputfolder / mediapath.name):
            copy_strategy(str(mediapath), str(outputfolder))
        else:
            num_skipped += 1

        num_transferred += 1

        logger(f"Organized {num_transferred} of {length} files ({num_skipped} skipped; already exist).\r", end="")
    logger("")

    return num_transferred


def sort_images(albumpath, game_ids):
    """
    Transfer all jpg images

    Parameters:
        albumpath: Nintendo Album directory path
        game_ids: dictionary mapping screenshot ids to filesafe game names

    Returns: None
    """

    screenshotlist = sorted(
        Path(albumpath).glob(
            "[0-9][0-9][0-9][0-9]/[0-9][0-9]/[0-9][0-9]/*.jpg")
    )

    if len(screenshotlist) != 0:
        logger("Organizing screenshots...")
        check_folders(screenshotlist, game_ids)
    else:
        logger("No screenshots found!")


def sort_videos(albumpath, game_ids):
    """
    Transfer all mp4 images

    Parameters:
        albumpath: Nintendo Album directory path
        game_ids: dictionary mapping screenshot ids to filesafe game names

    Returns: None
    """

    videolist = sorted(
        Path(albumpath).glob(
            "[0-9][0-9][0-9][0-9]/[0-9][0-9]/[0-9][0-9]/*.mp4")
    )

    if len(videolist) != 0:
        logger("\nOrganizing videos...")
        check_folders(videolist, game_ids)
    else:
        logger("\nNo videos found!")


def main(args):
    """
    Main function that organizes all the things

    Parameters:
        args: argparse object

    Returns: None
    """
    global logger

    if args.quiet:
        logger = no_print

    if args.no_screenshots and args.no_videos:
        logger("Not transfering screenshots and videos. Exiting")
        return

    game_ids = get_gameids(args.update_cache)

    # If only updating cache, don't process files
    if args.update_cache:
        logger("Cache update complete. Exiting.")
        return

    # Check if albumpath is provided when not just updating cache
    if args.albumpath is None:
        logger("Error: albumpath is required when not using --update-cache only")
        sys.exit(1)

    # Check if user pointed towards Nintendo/ instead of Nintendo/Album
    point_nintendo_folder = args.albumpath.joinpath("Album")
    if os.path.exists(point_nintendo_folder):
        args.albumpath = point_nintendo_folder

    if not args.no_screenshots:
        sort_images(args.albumpath, game_ids)

    if not args.no_videos:
        sort_videos(args.albumpath, game_ids)

    logger("Done!")


if __name__ == "__main__":
    import argparse

    # File ran directly - parse arguments. Done here to allow other scripts
    # to import functions declared in here. Not sure why you would need
    # to do that but it's supported I guess.

    parser = argparse.ArgumentParser(
        description="Automatically organize and timestamp \
                 your Nintendo Switch screenshots and clips")

    parser.add_argument("--version", action="version",
                        version=f"%(prog)s {PROGRAM_VERSION}")

    parser.add_argument("albumpath",
                        metavar="ALBUMPATH",
                        type=Path,
                        nargs='?',
                        help="'Nintendo/Album' folder from your SD card.")

    parser.add_argument("-u",
                        "--update-cache",
                        action="store_true",
                        help="Update cached games list via online \
                        database. Requires key.txt to be present")

    parser.add_argument("--overwrite",
                        action="store_true",
                        help="Overwrite file if it already exists")

    parser.add_argument("--no-videos",
                        action="store_true",
                        help="Do not organize video (.mp4) files")

    parser.add_argument("--no-screenshots",
                        action="store_true",
                        help="Do not organize image (.jpg) files")

    parser.add_argument("-q",
                        "--quiet",
                        action="store_true",
                        help="Don't print standard out to console")

    parser.add_argument("-c",
                        "--copy",
                        action="store_true",
                        help="Copy file instead of hard link")

    args = parser.parse_args()
    main(args)
