"""
Make sure the ground-truth beats are accurate
"""
from pydub import AudioSegment
from pydub.playback import play
import os

def play_ground_truth(audio_file, ground_truth, tick_path="./samples/tick.mp3"):
    """
    Render the ground truth data onto the audio file and play

    Parameters:
        audio_file              Path to the audio file
        ground_truth            Path to the txt file demarcating beat locations
        tick_path               Path to a file containing ticks to be rendered
    """
    # TODO I think songs are too fast? Not sure why they're so obviously out-of-sync
    song = AudioSegment.from_file(audio_file)
    downbeat = AudioSegment.from_file(tick_path).apply_gain(3)
    tick = AudioSegment.from_file(tick_path).apply_gain(-3)
    with open(ground_truth) as gt:
        for line in gt:
            line = line.strip('\n').split(' ')

            if line[0] == "offset":     # Data has already been verified
                return

            # Location of tick, in ms
            time = int(1000 * float(line[0])) - 30
            print(time)

            # 1, 2, 3, or 4
            # TODO Use
            mark = int(line[2])

            # TODO Use ternary
            if mark == 1:
                song = song.overlay(downbeat, position=time)
            else:
                song = song.overlay(tick, position=time)

    play(song)


def main():
    # TODO Argparse
    data_path = "./data"

    # Walk the dataset
    for root, dirs, files in os.walk(data_path):
        for f in files:
            if f.endswith(".wav"):  # TODO Make extension generic
                filename = os.path.splitext(f)[0]
                gt = filename + ".txt"
                
                # Add ticks for every beat in ground truth
                candidate = render_ground_truth(os.path.join(root, f), os.path.join(root, gt))

                # Play the audio to verify

    


if __name__ == "__main__":
    main()
