# face_recog_video_debug.py
import os
import time
import sys
import argparse
import cv2
import numpy as np
import face_recognition


# ---------- CONFIG (defaults) ----------
DEFAULT_VIDEO_SRC = 0           # 0 means webcam; can be integer index or path string
DEFAULT_ENC_FILE = "known_encodings.npy"
MODEL = "hog"                  # "hog" or "cnn" (cnn is slower)
TOLERANCE = 0.5
SCALE_FAC = 0.5                 # downsizing factor for speed (1.0 = original size)
PROCESS_EVERY_N_FRAMES = 1      # skip frames to speed up (1 = process all)
OUTPUT_FILE = "output_debug.mp4"
USE_HAAR_FALLBACK = True        # if face_recognition finds 0 faces, try Haar cascade
# ---------------------------------------


def load_known(enc_file):
    if not os.path.exists(enc_file):
        print(f"[ERROR] Encodings file not found: {enc_file}")
        sys.exit(1)
    data = np.load(enc_file, allow_pickle=True).item()
    # data expected: { name: encoding } or { name: array_of_encodings }
    flat_names = []
    flat_encs = []
    for name, val in data.items():
        if val is None:
            continue
        arr = np.array(val)
        if arr.ndim == 1 and arr.size == 128:
            flat_names.append(name)
            flat_encs.append(arr)
        elif arr.ndim == 2 and arr.shape[1] == 128:
            for row in arr:
                flat_names.append(name)
                flat_encs.append(row)
        else:
            # try treating as iterable of encodings
            try:
                for row in arr:
                    row = np.array(row)
                    if row.ndim == 1 and row.size == 128:
                        flat_names.append(name)
                        flat_encs.append(row)
            except Exception:
                print(f"[WARN] Unknown encoding format for {name}, skipping")

    print(f"[INFO] Loaded {len(set(flat_names))} people, {len(flat_encs)} total encodings")
    return flat_names, flat_encs


def open_video(src):
    print("[INFO] Opening video source:", src)
    # if src is numeric string or int, convert to int for webcam index
    try:
        src_val = int(src)
    except Exception:
        src_val = src
    cap = cv2.VideoCapture(src_val)
    if not cap.isOpened():
        print("[ERROR] Cannot open video source:", src)
        return None
    return cap


def prepare_writer(cap, out_file):
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    out_w = int(w)
    out_h = int(h)
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(out_file, fourcc, fps, (out_w, out_h))
    print(f"[INFO] Output writer prepared: {out_file} (fps={fps}, size={out_w}x{out_h})")
    return writer


def haar_faces(gray, scale=1.1):
    import os
    cascade_name = "haarcascade_frontalface_default.xml"
    cascade_path = None
    # try the normal cv2.data.haarcascades location first
    try:
        cascade_path = cv2.data.haarcascades + cascade_name
    except Exception:
        # fallback: attempt to locate cascade next to the cv2 package
        base = os.path.dirname(cv2.__file__)
        candidates = [
            os.path.join(base, "data", cascade_name),
            os.path.join(base, "haarcascades", cascade_name),
            os.path.join(base, cascade_name),
        ]
        for c in candidates:
            if os.path.exists(c):
                cascade_path = c
                break

    if not cascade_path or not os.path.exists(cascade_path):
        # graceful fallback: report and return empty list
        print(f"[WARN] Haar cascade file not found (tried cv2.data and common locations). Expected {cascade_name}.")
        return []

    cascade = cv2.CascadeClassifier(cascade_path)
    if cascade.empty():
        print(f"[WARN] Failed to load Haar cascade from: {cascade_path}")
        return []

    rects = cascade.detectMultiScale(gray, scaleFactor=scale, minNeighbors=4, minSize=(30, 30))
    out = []
    for (x, y, w, h) in rects:
        top, left, bottom, right = y, x, y + h, x + w
        out.append((top, right, bottom, left))
    return out


def parse_args():
    p = argparse.ArgumentParser(description="Realtime face recognition using known/ folder encodings")
    p.add_argument("--source", "-s", default=DEFAULT_VIDEO_SRC, help="Video source (0 for webcam or path to file)")
    p.add_argument("--enc", "-e", default=DEFAULT_ENC_FILE, help="Encodings .npy file")
    p.add_argument("--out", "-o", default=OUTPUT_FILE, help="Output video file (set empty to disable writing)")
    p.add_argument("--model", "-m", default=MODEL, choices=["hog", "cnn"], help="Face detection model")
    p.add_argument("--tolerance", "-t", type=float, default=TOLERANCE, help="Matching tolerance (lower is stricter)")
    p.add_argument("--scale", type=float, default=SCALE_FAC, help="Resize scale for processing")
    p.add_argument("--skip", type=int, default=PROCESS_EVERY_N_FRAMES, help="Process every N frames")
    return p.parse_args()


def main():
    args = parse_args()

    global MODEL, TOLERANCE, SCALE_FAC, PROCESS_EVERY_N_FRAMES
    MODEL = args.model
    TOLERANCE = args.tolerance
    SCALE_FAC = args.scale
    PROCESS_EVERY_N_FRAMES = max(1, args.skip)

    names_flat, encs_flat = load_known(args.enc)
    if not encs_flat:
        print("[ERROR] No known encodings loaded. Exiting.")
        return

    cap = open_video(args.source)
    if cap is None:
        return

    writer = None
    if args.out:
        writer = prepare_writer(cap, args.out)

    frame_idx = 0
    processed = 0
    total_faces_found = 0
    t0 = time.time()

    window_name = "Face Recognition"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)

    while True:
        ret, frame = cap.read()
        if not ret:
            print("[INFO] End of video / cannot read frame.")
            break
        frame_idx += 1

        if (frame_idx % PROCESS_EVERY_N_FRAMES) != 0:
            if writer:
                writer.write(frame)
            cv2.imshow(window_name, frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
            continue

        small = cv2.resize(frame, (0, 0), fx=SCALE_FAC, fy=SCALE_FAC)
        rgb_small = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)

        face_locations = face_recognition.face_locations(rgb_small, model=MODEL)
        face_encodings = face_recognition.face_encodings(rgb_small, face_locations)

        if frame_idx % 30 == 0:
            print(f"[DEBUG] frame {frame_idx}: small_shape={rgb_small.shape}, face_locations_found={len(face_locations)}")

        names_in_frame = []
        if len(face_locations) == 0 and USE_HAAR_FALLBACK:
            gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
            haar_locs = haar_faces(gray)
            if len(haar_locs) > 0:
                print(f"[DEBUG] Haar fallback found {len(haar_locs)} faces on frame {frame_idx}")
                face_locations = haar_locs
                face_encodings = face_recognition.face_encodings(rgb_small, face_locations)

        # match faces to known encodings (flat list)
        for enc in face_encodings:
            name = "Unknown"
            if len(encs_flat) > 0:
                matches = face_recognition.compare_faces(encs_flat, enc, TOLERANCE)
                if True in matches:
                    name = names_flat[matches.index(True)]
                else:
                    # fallback to distance-based name (closest)
                    dists = face_recognition.face_distance(encs_flat, enc)
                    if len(dists) > 0:
                        best_idx = int(np.argmin(dists))
                        if dists[best_idx] <= TOLERANCE:
                            name = names_flat[best_idx]
            names_in_frame.append(name)

        for (top, right, bottom, left), name in zip(face_locations, names_in_frame):
            top = int(top / SCALE_FAC)
            right = int(right / SCALE_FAC)
            bottom = int(bottom / SCALE_FAC)
            left = int(left / SCALE_FAC)
            cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)
            cv2.putText(frame, name, (left, top - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

        total_faces_found += len(face_locations)
        processed += 1

        if writer:
            writer.write(frame)

        cv2.imshow(window_name, frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            print("[INFO] Quit key pressed, exiting")
            break

    dt = time.time() - t0
    print(f"[INFO] Done. Frames processed: {processed}, total_faces_found: {total_faces_found}, time: {dt:.2f}s, avg fps: {processed/dt:.2f}")
    cap.release()
    if writer:
        writer.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
