"""
Downloads the data used to train the model
"""
from __future__ import unicode_literals
import pandas as pd
import requests
import json
import urllib.request
import os
from bs4 import BeautifulSoup
from ytsearch import youtube as yts
import time
from ext.align_text_matches import align_one_file
from fuzzywuzzy import fuzz
import youtube_dl


def youtube_download(url, path, filename, force=False, fmt="wav"):
    """
    Downloads a youtube video with the given URL as a wav file to the given
    path using the given filename

    Paramaters:
        url         Video url
        filename    Desired filename of the wav file
        force       If True, will overwrite existing files of the same name
        fmt         Audio format
    """
    # If file exists, skip
    if os.path.exists(f"{path}/{filename}.{fmt}") and not force:
        print(f"{path}/{filename}.{fmt} exists")     # For debugging
        return None

    # Uses youtube-dl to download audio-only
    ydl_opts = {
        # 'format': fmt,
        'format': '140',    # 140 = m4a compression; audio only
        'noplaylist': 'True',
        'outtmpl': path + "/" + filename + ".%(ext)s",
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': fmt
        }],
    }
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])


def get_first_result(keywords, maxlen):
    """
    Helper function to find the first youtube result using the given keywords
    with length shorter than maxlen

    Returns a url to the selected video
    """
    # TODO Iterate through results to get top result within time constraints
    raw = yts.raw_search(keywords)
    suffix = None
    for item in raw['items']:
        if item['kind'] == 'youtube#searchResult' and item['id']['kind'] == 'youtube#video':
            print(item['id'])
            suffix = item['id']['videoId']
            break
    return "https://youtube.com/watch?v=" + suffix


def search_and_download(keywords, path, filename=None, maxlen=None):
    """
    Downloads the first result on youtube when searching using the given
    keywords

    Parameters:
        keywords    The keywords to be searched
        path        Folder to write the downloaded video
        filename    Name of the file to be written
        maxlen      Maximum length to accept
    """
    try:
        link = get_first_result(keywords, maxlen)

        # Download result to disk
        youtube_download(
            link,
            path,
            filename if filename is not None else keywords,
            fmt="wav"
        )
    except youtube_dl.utils.DownloadError:
        search_and_download(keywords, path, filename, maxlen)


def _get_h5(artist, song, h5):
    """
    Helper function to get the h5 file corresponding to the given song

    Parameters:
        artist      Name of the artist (used to find the folder)
        song        Name of the song (used to find the actual h5 file)

    Returns:
        Full path to h5 file if found
        None if not
    """
    # Normalize names
    artist = artist.lower().replace(" ", "_")
    song = song.lower().replace(" ", "_").replace("'", "_")

    # Find the file
    try:
        artistpath = h5 + artist + "/"
        albums = os.listdir(artistpath)

        for album in albums:
            albumpath = artistpath + album + "/"

            for songfile in os.listdir(albumpath):
                # See if the song exists using Levenshtein distance
                songfile_clean = songfile.lower().replace('-', '.')
                songfile_clean = songfile_clean.split('.')[1]

                if fuzz.partial_ratio(songfile_clean, song) > 90:
                    return albumpath + songfile

    except FileNotFoundError:
        print("Not found")
        return None


def generate_data(lmd, h5, audio):
    """
    Downloads data from the million song dataset

    Parameters:
        lmd         Path to the root of the lakh midi dataset (must end in a /)
        h5          Path to a directory of HDF5 files
        audio       Path to the root of the directory to download the audio to
    """
    """
    Steps:
        1) Get a MIDI file from the MIDI directory [done]
        2) Get the name of a song based on the filename
           (from the MIDI directory) [done]
        3) Get the name of the artist from the directory name [done]
        4) Use the above to get keywords [done]
        5) Find the corresponding hd5 alignment file [done]
        6) Download the first youtube result satisfying those keywords [done]
        7) Verify that the MIDI matches the audio using align_one_file() in
           ./ext/align_text_matches.py
           - This should return a number representing the success of the
             alignment. If the alignment succeeds, write the file. Otherwise,
             do not.
    """
    # TODO Once pipeline is working, iterate through all files, not just one
    artist = 'Michael Jackson'  # TODO Don't hardcode
    artist_dir = lmd + artist + "/"
    midifile = os.listdir(artist_dir)[3]
    songname = midifile.split('.')[0]

    # TODO Use multiple sets of keywords (add audio only to the end, for ex)
    keywords = songname + " " + artist

    # Search for audio features alignment file
    audio_features_filename = _get_h5(artist, songname, h5)

    if audio_features_filename is None:
        return  # TODO Should be continue when iterating

    # Download audio
    # TODO Max len should depend on MIDI
    search_and_download(keywords, audio, filename=songname, maxlen=500)

    # TODO Come up with a place to store generated features (MIDI and audio)
    # Perform alignment
    alignment_results = align_one_file(
            audio + songname + ".wav",
            artist_dir + midifile,
            audio_features_filename=audio_features_filename,
            output_diagnostics_filename=audio + songname + "-align.h5",
            midi_features_filename=audio + songname + "-midi-features.h5",
            output_midi_filename=audio + songname + "-midi.mid"
    )

    print(alignment_results)


def get_acoustic_brainz(path):
    """
    Downloads data from the acoustic brainz dataset, which contains
    labelled audio files

    Parameters:
        path        Path to the folder to be populated with the data. The
                    folder should contain a CSV with a list of musicbrainz IDs
                    called dataset_annotations.csv
    """
    # TODO Don't always assume path ends in a /
    path_to_ids = path + "dataset_annotations.csv"

    # Read the csv into a pandas dataframe
    df = pd.read_csv(path_to_ids, delimiter=",", encoding="ascii")

    # Download the ground truth data for each MB ID
    for index, value in df['ID'].iteritems():
        # Download data to json
        url = f"https://acousticbrainz.org/api/v1/{value}/low-level"
        request = requests.get(url)
        data = request.json()

        # Get title
        title = data['metadata']['tags']['title'][0]
        print(title)

        # Make a subdirectory to hold the song and its data
        song_dir = path + title + "/"
        if not os.path.exists(song_dir):
            os.makedirs(song_dir)

        # Write json to disk
        dataFile = open(song_dir + title + ".json", "w")
        dataFile.write(json.dumps(data, indent=4, sort_keys=True))
        dataFile.close()

        # TODO Need to take track listing into account somehow and add better
        # searching (to avoid downloading someone else's channel with the same
        # name)

        # Only use keywords that exist
        # Keywords: title + artist + composer
        # Seems like title + artist is the best in most situations, even
        # if the composer exists

        # Search for top result of title on yt and download
        search_and_download(title, song_dir)


def get_isophonics(rootdir):
    """
    Prerequisites: Need to have isophonics annotations in ./data/

    Iterate through csv files and download their song from youtube
    """
    for subdir, dirs, files in os.walk(rootdir):
        for f in files:
            if f.endswith("txt"):
                filename = os.path.splitext(f)[0]

                # If song already downloaded, skip
                if os.path.exists(f"{subdir}/{filename}.wav"):
                    print("exists!")     # For debugging
                    continue

                # Do some crazy parsing to get the song name from the filename
                song_name = os.path.splitext(f)[0][5:].replace("_", " ")

                search_and_download(song_name, subdir, filename=filename)


if __name__ == "__main__":
    # Paths to data (if unclear, refactor names)
    lmd = "./data/clean_midi/"
    h5 = "./data/uspopHDF5/"
    audio = "./data/generated/audio/"
    isophonics = "./data"

    get_isophonics(isophonics)
