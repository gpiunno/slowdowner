import os
import numpy as np
import librosa
import sounddevice as sd
import moviepy as mp


def extract_audio_from_video(video_path:str, save_flag:bool=False, output_path:str=None):
    """
    Extracts the audio track from a video and returns it as a NumPy array with sample rate.

    :param str video_path: Path to the input video file.
    :param bool save_flag: If True, saves the extracted audio to output_path.
    :param str output_path: Path to save the extracted audio file (if save_flag is True).

    :return: Tuple (audio_array, sample_rate) where audio_array is a NumPy array of the audio samples
             and sample_rate is the sample rate of the audio.
    """
    print(f"Extracting audio from {video_path}...")
    temp_audio_path = "temp_extracted_audio.wav"
    video = mp.VideoFileClip(video_path)
    if save_flag:
        if output_path is None:
            raise ValueError("Output path must be provided if save_flag is True.")
        video.audio.write_audiofile(output_path)  # removed verbose/logger
        y, sr = librosa.load(output_path, sr=None)
    else:
        video.audio.write_audiofile(temp_audio_path)  # removed verbose/logger
        y, sr = librosa.load(temp_audio_path, sr=None)
        os.remove(temp_audio_path)
    return y, sr


def load_audio(audio_path:str):
    """
    Loads an audio file (wav, mp3, etc.) and returns it as a NumPy array with sample rate.

    :param str audio_path: Path to the audio file.

    :return: Tuple (audio_array, sample_rate) where audio_array is a NumPy array of the audio samples
             and sample_rate is the sample rate of the audio.
    """
    print(f"Loading audio from {audio_path}...")
    y, sr = librosa.load(audio_path, sr=None)
    return y, sr


def extract_time_window(audio_array: np.ndarray, sr: int, start_time: float, end_time: float) -> np.ndarray:
    """
    Extracts a portion of the audio trace between start_time and end_time (in seconds).

    :param np.ndarray audio_array: The audio samples as a NumPy array.
    :param int sr: The sample rate of the audio.
    :param float start_time: Start time in seconds.
    :param float end_time: End time in seconds.

    :return: NumPy array containing the extracted audio segment.
    """
    start_sample = int(start_time * sr)
    end_sample = int(end_time * sr)
    return audio_array[start_sample:end_sample]


def slow_down_audio(audio_segment: np.ndarray, slowdown_factor: float) -> np.ndarray:
    """
    Slows down an audio segment without changing its pitch using librosa.

    :param np.ndarray audio_segment: The audio segment to slow down.
    :param float slowdown_factor: The factor by which to slow down the audio (e.g., 2.0 halves the speed).

    :return: NumPy array of the slowed down audio segment.
    """
    print(f"Slowing down audio by a factor of {slowdown_factor} (without pitch change)...")
    return librosa.effects.time_stretch(audio_segment, rate=1.0 / slowdown_factor)


def play_audio_loop(audio_array: np.ndarray, sr: int, nloops: int = 1) -> None:
    """
    Plays the given audio array in a loop for a specified number of times.

    :param np.ndarray audio_array: The audio samples as a NumPy array.
    :param int sr: The sample rate of the audio.
    :param int nloops: Number of times to loop playback (default is 1).

    :return: None
    """
    print("Playing slowed audio in loop. Press Ctrl+C to stop.")
    try:
        n = 1
        while n <= nloops:
            sd.play(audio_array, sr)
            sd.wait()
            n += 1
    except KeyboardInterrupt:
        print("\nLoop playback stopped.")