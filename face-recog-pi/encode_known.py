import os
import cv2
import numpy as np
import face_recognition

KNOWN_DIR = "known"
OUT_FILE = "known_encodings.npy"
# when sampling videos, skip this many frames between analyses
VIDEO_FRAME_SKIP = 30
# consider two encodings the same if distance < this threshold
DUPLICATE_DISTANCE = 0.45

def add_unique_encoding(existing_list, new_enc):
	"""Add new_enc to existing_list if it's not very close to any existing encoding."""
	if new_enc is None:
		return
	if not existing_list:
		existing_list.append(new_enc)
		return
	dists = face_recognition.face_distance(existing_list, new_enc)
	if len(dists) == 0 or np.min(dists) > DUPLICATE_DISTANCE:
		existing_list.append(new_enc)


def is_image(fname):
	return fname.lower().endswith((".jpg", ".jpeg", ".png", ".bmp"))


def is_video(fname):
	return fname.lower().endswith((".mp4", ".mov", ".avi", ".mkv"))


def extract_encodings_from_image(path):
	img = face_recognition.load_image_file(path)
	encs = face_recognition.face_encodings(img)
	return encs


def extract_encodings_from_video(path, skip=VIDEO_FRAME_SKIP):
	encs = []
	cap = cv2.VideoCapture(path)
	if not cap.isOpened():
		print("  WARNING: cannot open video:", path)
		return encs
	idx = 0
	while True:
		ret, frame = cap.read()
		if not ret:
			break
		idx += 1
		if (idx % skip) != 0:
			continue
		# convert to RGB for face_recognition
		rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
		locs = face_recognition.face_locations(rgb, model="hog")
		if not locs:
			continue
		frame_encs = face_recognition.face_encodings(rgb, locs)
		for e in frame_encs:
			encs.append(e)
	cap.release()
	return encs


def main():
	encodings_dict = {}
	print("Scanning known folder:", KNOWN_DIR)
	if not os.path.isdir(KNOWN_DIR):
		print("Known folder not found:", KNOWN_DIR)
		return

	for fname in sorted(os.listdir(KNOWN_DIR)):
		path = os.path.join(KNOWN_DIR, fname)
		if not os.path.isfile(path):
			continue
		name = os.path.splitext(fname)[0]
		print("Processing", fname, "as", name)
		person_list = encodings_dict.get(name, [])

		try:
			if is_image(fname):
				img_encs = extract_encodings_from_image(path)
				if not img_encs:
					print("  WARNING: no face found in", fname)
				for e in img_encs:
					add_unique_encoding(person_list, e)

			elif is_video(fname):
				vid_encs = extract_encodings_from_video(path)
				if not vid_encs:
					print("  WARNING: no faces found in video", fname)
				for e in vid_encs:
					add_unique_encoding(person_list, e)
			else:
				print("  Skipping unsupported file type:", fname)
				continue
		except Exception as ex:
			print("  ERROR processing", fname, "->", ex)

		if person_list:
			encodings_dict[name] = np.array(person_list)

	if not encodings_dict:
		print("No encodings created. Put at least one clear face image or video in known/")
	else:
		np.save(OUT_FILE, encodings_dict)
		print("Saved encodings to", OUT_FILE, " with", len(encodings_dict), "people")


if __name__ == '__main__':
	main()
