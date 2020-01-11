"""
Downloads the data used to train the model
"""
import pandas as pd
import requests
import json
import urllib.request
import os
from bs4 import BeautifulSoup


def youtube_download(url, path, filename, force=False, fmt="wav"):
    """
    Downloads a youtube video with the given URL as a wav file to the given
    path using the given filename

    Paramaters:
        url         Video url
        filename    Desired filename of the wav file
        force       If True, will overwrite existing files
        fmt         Audio format
    """
    # If file exists, skip
    if os.path.exists(path + filename + "." + fmt) and not force:
        print("exists")
        return None

    # TODO Use youtube-dl instead


def first_youtube_result(keywords, path, filename=None):
    """
    Downloads the first result on youtube when searching using the given
    keywords

    Parameters:
        keywords    The keywords to be searched
        path        Folder to write the downloaded video
        filename    Name of the file to be written
    """
    # Get link to top result
    query = urllib.parse.quote(keywords)
    url = "https://www.youtube.com/results?search_query=" + query
    response = urllib.request.urlopen(url)
    html = response.read()
    soup = BeautifulSoup(html, 'html.parser')
    vid = soup.find(attrs={'class': 'yt-uix-tile-link'})
    result = "https://www.youtube.com" + vid['href']

    # Download result to disk
    youtube_download(
        result,
        path,
        filename if filename is not None else keywords,
        fmt="webm"
    )


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

        # Write json to disk
        dataFile = open(path + title + ".json", "w")
        dataFile.write(json.dumps(data, indent=4, sort_keys=True))
        dataFile.close()

        # Search for top result of title on yt and download
        first_youtube_result(title, path)


if __name__ == "__main__":
    get_acoustic_brainz("./data/acousticbrainz/")
