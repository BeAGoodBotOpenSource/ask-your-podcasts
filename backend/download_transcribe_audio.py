import requests
from bs4 import BeautifulSoup
import os
import re
import whisper

RSS_URL = "https://feeds.acast.com/public/shows/64c86a5585617f0011a4a263"
DOWNLOAD_DIR = "downloaded_audios"
TRANSCRIBE_DIR = "transcribed_texts"

# Load the Whisper model
model = whisper.load_model("base")

def sanitize_filename(filename):
    """Remove or replace characters that are problematic in filesystem names."""
    return re.sub(r'(?u)[^-\w.]', '', filename)

def download_audio(url, filename):
    response = requests.get(url, stream=True)
    with open(filename, 'wb') as file:
        for chunk in response.iter_content(chunk_size=1024 * 1024):  # 1MB chunks
            if chunk:
                file.write(chunk)
    print(f"Downloaded {filename}")

def transcribe_audio_file(filepath):
    result = model.transcribe(filepath)
    return result["text"]

def main():
    response = requests.get(RSS_URL)
    response.raise_for_status()  # Raise an error if the request failed

    soup = BeautifulSoup(response.content, "xml")

    # Ensure the directories exist
    if not os.path.exists(DOWNLOAD_DIR):
        os.makedirs(DOWNLOAD_DIR)
    if not os.path.exists(TRANSCRIBE_DIR):
        os.makedirs(TRANSCRIBE_DIR)

    # Loop through each item in the RSS feed
    for index, item in enumerate(soup.find_all('item'), 1):  # index starts at 1
        episode_name = item.title.string if item.title else ""
        audio_url = item.enclosure['url']

        # Use the index as episode number and sanitize the episode name to ensure it's safe as a filename
        safe_episode_name = sanitize_filename(episode_name)
        audio_filename = os.path.join(DOWNLOAD_DIR, f"Episode{index}-{safe_episode_name}.mp3")
        txt_filename = os.path.join(TRANSCRIBE_DIR, f"Episode{index}-{safe_episode_name}.txt")

        # Check if the audio file exists. If not, download it.
        if not os.path.exists(audio_filename):
            download_audio(audio_url, audio_filename)

        # Check if the transcription file exists. If not, transcribe and save.
        if not os.path.exists(txt_filename):
            transcription = transcribe_audio_file(audio_filename)
            with open(txt_filename, "w+") as txt_file:
                txt_file.write(transcription)
            print(f"Transcribed {audio_filename} to {txt_filename}")

if __name__ == "__main__":
    main()
