#!/usr/bin/env python3
"""
Enroll a face for image identification.

Usage:
    enroll-face --name "Kabir" --file photo.jpg
    enroll-face --list
    enroll-face --identify --file photo.jpg
    enroll-face --path /custom/path/faces.jsonl --name "Kabir" --file photo.jpg
"""

import argparse
import os

from .face import FaceStore

_DEFAULT_PATH = os.path.join("data", "memory", "faces.jsonl")


def main():
    parser = argparse.ArgumentParser(description="Enroll a face for image identification")
    parser.add_argument("--name", help="Person name to enroll")
    parser.add_argument("--file", help="Path to a JPEG image file")
    parser.add_argument("--list", action="store_true", help="List enrolled faces and exit")
    parser.add_argument("--identify", action="store_true", help="Identify the person in --file")
    parser.add_argument("--threshold", type=float, default=0.6, help="Match threshold (default: 0.6)")
    parser.add_argument("--path", default=_DEFAULT_PATH, help=f"Path to faces file (default: {_DEFAULT_PATH})")
    args = parser.parse_args()

    store = FaceStore(path=args.path)

    if args.list:
        faces = store.faces()
        if not faces:
            print("No faces enrolled yet.")
        else:
            for name in faces:
                print(f"  {name}: {store.sample_count(name)} sample(s)")
        return

    if not args.file:
        parser.error("--file is required")

    with open(args.file, "rb") as f:
        jpeg_bytes = f.read()

    if args.identify:
        if not store.faces():
            print("No faces enrolled yet. Enroll someone first.")
            return
        name = store.identify(jpeg_bytes, threshold=args.threshold)
        print(f"Identified: {name}" if name else "Unknown face (no match within threshold)")
        return

    if not args.name:
        parser.error("--name is required unless --list or --identify is specified")

    count = store.enroll(args.name, jpeg_bytes)
    if count == 0:
        print(f"No face detected in {args.file}.")
    else:
        print(f"Enrolled '{args.name}' — now has {count} sample(s).")
        print(f"Profiles saved to: {store.path}")


if __name__ == "__main__":
    main()
