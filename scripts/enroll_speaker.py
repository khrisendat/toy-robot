#!/usr/bin/env python3
"""
Enroll a speaker for voice identification.

Usage:
    # Record from microphone (default 8 seconds):
    python scripts/enroll_speaker.py --name "Kabir"

    # Record a specific duration:
    python scripts/enroll_speaker.py --name "Dada" --duration 12

    # Use an existing WAV file:
    python scripts/enroll_speaker.py --name "Mama" --file samples/mama.wav

    # List enrolled speakers:
    python scripts/enroll_speaker.py --list

    # Test identification (record and see who the model thinks it is):
    python scripts/enroll_speaker.py --identify
"""

import argparse
import io
import os
import sys
import wave

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.lib.speaker_id import SpeakerIdentifier


def record_wav(duration: int) -> bytes:
    import pyaudio

    RATE = 16000
    CHUNK = 1024
    pa = pyaudio.PyAudio()
    stream = pa.open(
        format=pyaudio.paInt16,
        channels=1,
        rate=RATE,
        input=True,
        frames_per_buffer=CHUNK,
    )

    print(f"Recording for {duration}s... speak now")
    frames = []
    for _ in range(int(RATE / CHUNK * duration)):
        frames.append(stream.read(CHUNK, exception_on_overflow=False))
    print("Done recording.")

    stream.stop_stream()
    stream.close()
    pa.terminate()

    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(RATE)
        wf.writeframes(b"".join(frames))
    return buf.getvalue()


def main():
    parser = argparse.ArgumentParser(description="Enroll a speaker for voice identification")
    parser.add_argument("--name", help="Speaker name (e.g. 'Kabir')")
    parser.add_argument("--duration", type=int, default=8, help="Recording duration in seconds (default: 8)")
    parser.add_argument("--file", help="Path to an existing WAV file to use instead of recording")
    parser.add_argument("--list", action="store_true", help="List enrolled speakers and exit")
    parser.add_argument("--identify", action="store_true", help="Record and identify the speaker")
    args = parser.parse_args()

    sid = SpeakerIdentifier()

    if args.list:
        speakers = sid.speakers()
        if not speakers:
            print("No speakers enrolled yet.")
        else:
            for name in speakers:
                print(f"  {name}: {sid.sample_count(name)} sample(s)")
        return

    if args.identify:
        if not sid.speakers():
            print("No speakers enrolled yet. Enroll someone first.")
            return
        wav_bytes = record_wav(args.duration)
        name = sid.identify(wav_bytes)
        if name:
            print(f"Identified: {name}")
        else:
            print("Unknown speaker (no match above threshold)")
        return

    if not args.name:
        parser.error("--name is required unless --list or --identify is specified")

    if args.file:
        with open(args.file, "rb") as f:
            wav_bytes = f.read()
        print(f"Using file: {args.file}")
    else:
        wav_bytes = record_wav(args.duration)

    count = sid.enroll(args.name, wav_bytes)
    print(f"Enrolled '{args.name}' — now has {count} sample(s).")
    print(f"Profiles saved to: {sid.path}")


if __name__ == "__main__":
    main()
