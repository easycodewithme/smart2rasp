#!/usr/bin/env python3
"""Enroll a new person by capturing images from the webcam, encode known faces,
and optionally start realtime recognition.

Usage examples:
  # interactive capture (5 samples), then encode, then run realtime recognition
  python enroll_and_run.py --name alice --samples 5 --run

  # only capture and encode (don't start recognition)
  python enroll_and_run.py --name bob --samples 3

The script saves images to the `known/` directory as <name>_<ts>_<i>.jpg,
then runs `encode_known.py` (must be in the same folder) to regenerate
`known_encodings.npy`. If --run is provided, it will launch
`face_recog_video_debug.py` afterwards using the same Python interpreter.
"""

import argparse
import os
import sys
import time
import subprocess
from datetime import datetime

try:
    import cv2
except Exception as e:
    print("Error: OpenCV (cv2) is required. Install with `pip install opencv-python` or via conda.")
    raise


KNOWN_DIR = "known"


def ensure_known_dir():
    if not os.path.isdir(KNOWN_DIR):
        os.makedirs(KNOWN_DIR, exist_ok=True)


def capture_samples(name, samples=5, delay=1.0, auto=True):
    """Capture `samples` images from the default webcam.

    If auto=True, captures automatically with a short countdown and delay.
    If auto=False, user must press 'c' to capture each sample or 'q' to quit.
    Returns list of saved file paths.
    """
    ensure_known_dir()
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        raise RuntimeError("Cannot open webcam (index 0). Check camera and permissions.")

    saved = []
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    idx = 0

    print(f"Starting capture for '{name}'. Samples={samples}, auto={auto}")
    try:
        while idx < samples:
            ret, frame = cap.read()
            if not ret:
                print("Warning: cannot read frame from camera. Retrying...")
                time.sleep(0.5)
                continue

            display = frame.copy()
            label = f"{name} - sample {idx+1}/{samples}"
            cv2.putText(display, label, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)

            if auto:
                # show a short countdown
                for t in range(3, 0, -1):
                    disp2 = display.copy()
                    cv2.putText(disp2, f"Capturing in {t}", (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 255), 2)
                    cv2.imshow("enroll", disp2)
                    if cv2.waitKey(1000) & 0xFF == ord('q'):
                        print("Quit pressed. Exiting capture loop.")
                        cap.release()
                        cv2.destroyAllWindows()
                        return saved

                # capture frame
                fname = f"{name}_{timestamp}_{idx+1}.jpg"
                path = os.path.join(KNOWN_DIR, fname)
                cv2.imwrite(path, frame)
                print("Saved", path)
                saved.append(path)
                idx += 1
                time.sleep(delay)

            else:
                cv2.imshow("enroll", display)
                key = cv2.waitKey(1) & 0xFF
                if key == ord('c'):
                    fname = f"{name}_{timestamp}_{idx+1}.jpg"
                    path = os.path.join(KNOWN_DIR, fname)
                    cv2.imwrite(path, frame)
                    print("Saved", path)
                    saved.append(path)
                    idx += 1
                elif key == ord('q'):
                    print("Quit pressed. Exiting capture loop.")
                    break

    finally:
        cap.release()
        cv2.destroyAllWindows()

    return saved


def run_encode(python=sys.executable):
    """Run encode_known.py using the same Python interpreter.
    Returns subprocess.CompletedProcess
    """
    cmd = [python, os.path.join(os.getcwd(), "encode_known.py")]
    print("Running:", " ".join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True)
    print(result.stdout)
    if result.returncode != 0:
        print("encode_known.py failed:")
        print(result.stderr)
    return result


def run_recognition(python=sys.executable, source=0, enc_file="known_encodings.npy", out_file="output_debug.mp4"):
    cmd = [python, os.path.join(os.getcwd(), "face_recog_video_debug.py"), "--source", str(source), "--enc", enc_file, "--out", out_file]
    print("Starting recognition with:", " ".join(cmd))
    # run and forward the output; this call will block until recognition exits
    proc = subprocess.run(cmd)
    return proc


def parse_args():
    p = argparse.ArgumentParser(description="Enroll a person from webcam, encode known faces, and optionally run realtime recognition.")
    p.add_argument("--name", required=False, help="Name/label to assign to captured images (if omitted, a popup will ask)")
    p.add_argument("--samples", type=int, default=5, help="Number of images to capture")
    p.add_argument("--delay", type=float, default=0.5, help="Delay between captures (seconds) when auto mode")
    p.add_argument("--auto", action="store_true", help="Auto-capture with countdown (default: manual capture) ")
    p.add_argument("--run", action="store_true", help="After encoding, run realtime recognition")
    p.add_argument("--source", default=0, help="Video source for recognition (default 0 for webcam)")
    p.add_argument("--enc", default="known_encodings.npy", help="Encodings file path")
    p.add_argument("--out", default="output_debug.mp4", help="Output video file path for recognition")
    return p.parse_args()


def main():
    args = parse_args()

    # default: manual capture unless --auto provided
    auto_mode = bool(args.auto)

    # If name not provided on CLI, prompt via a small popup (Tkinter) or fallback to console input
    name = args.name
    if not name:
        try:
            # Use tkinter simple dialog for a small popup
            import tkinter as tk
            from tkinter import simpledialog

            root = tk.Tk()
            root.withdraw()
            root.attributes('-topmost', True)
            name = simpledialog.askstring("Enroll user", "Enter name for enrollment:")
            root.destroy()
        except Exception:
            # fallback to console input
            try:
                name = input("Enter name for enrollment: ").strip()
            except Exception:
                name = None

    if not name:
        print("No name provided. Exiting.")
        return
    try:
        saved = capture_samples(name, samples=args.samples, delay=args.delay, auto=auto_mode)
        if not saved:
            print("No images captured. Exiting.")
            return
        print(f"Captured {len(saved)} images for '{name}'. Now running encoder...")
        r = run_encode()
        if r.returncode != 0:
            print("Encoding failed. See message above. Exiting.")
            return

        if args.run:
            print("Starting realtime recognition. Press 'q' in the window to quit.")
            run_recognition(source=args.source, enc_file=args.enc, out_file=args.out)
    except Exception as e:
        print("Error during enrollment:", e)


if __name__ == '__main__':
    main()
