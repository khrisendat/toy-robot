#!/usr/bin/env python3
"""
Enroll a speaker for voice identification.

Usage:
    enroll-speaker --name "Kabir"                         # record and enroll
    enroll-speaker --name "Dada" --duration 12            # longer recording
    enroll-speaker --name "Mama" --file samples/mama.wav  # enroll from file
    enroll-speaker --list                                  # list enrolled speakers
    enroll-speaker --identify                              # record and identify
    enroll-speaker --identify --file sample.wav            # identify from file
    enroll-speaker --path /custom/path/speakers.jsonl --name "Kabir"
"""

import argparse
import io
import os
import wave

from .speaker import SpeakerStore

_DEFAULT_PATH = os.path.join("data", "memory", "speakers.jsonl")


def _record_wav(duration: int) -> bytes:
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
    parser.add_argument("--name", help="Speaker name to enroll")
    parser.add_argument("--duration", type=int, default=8, help="Recording duration in seconds (default: 8)")
    parser.add_argument("--file", help="Path to an existing WAV file instead of recording")
    parser.add_argument("--list", action="store_true", help="List enrolled speakers and sample counts")
    parser.add_argument("--identify", action="store_true", help="Record (or use --file) and identify the speaker")
    parser.add_argument("--path", default=_DEFAULT_PATH, help=f"Path to speakers file (default: {_DEFAULT_PATH})")
    args = parser.parse_args()

    store = SpeakerStore(path=args.path)

    if args.list:
        speakers = store.speakers()
        if not speakers:
            print("No speakers enrolled yet.")
        else:
            for name in speakers:
                print(f"  {name}: {store.sample_count(name)} sample(s)")
        return

    if args.identify:
        if not store.speakers():
            print("No speakers enrolled yet. Enroll someone first.")
            return
        if args.file:
            with open(args.file, "rb") as f:
                wav_bytes = f.read()
            print(f"Using file: {args.file}")
        else:
            wav_bytes = _record_wav(args.duration)
        name = store.identify(wav_bytes)
        print(f"Identified: {name}" if name else "Unknown speaker (no match above threshold)")
        return

    if not args.name:
        parser.error("--name is required unless --list or --identify is specified")

    if args.file:
        with open(args.file, "rb") as f:
            wav_bytes = f.read()
        print(f"Using file: {args.file}")
    else:
        wav_bytes = _record_wav(args.duration)

    count = store.enroll(args.name, wav_bytes)
    print(f"Enrolled '{args.name}' — now has {count} sample(s).")
    print(f"Profiles saved to: {store.path}")


if __name__ == "__main__":
    main()
