# recognize_faces.py
import face_recognition
import argparse
import pickle
import cv2
import os

ap = argparse.ArgumentParser()
ap.add_argument(
    "-e",
    "--encodings",
    type=str,
    default="encodings.pickle",
    help="path to serialized db of facial encodings (default: encodings.pickle in project root)",
)
ap.add_argument("-i", "--image", required=True, help="path to input image")
args = vars(ap.parse_args())

encodings_path = args["encodings"]
if not os.path.isabs(encodings_path):
    encodings_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", encodings_path
    )
    encodings_path = os.path.normpath(encodings_path)

print(f"[INFO] Loading encodings from: {encodings_path}")

if not os.path.exists(encodings_path):
    raise FileNotFoundError(
        f"[ERROR] No encodings file found at {encodings_path}! Please run encode_faces.py first."
    )

with open(encodings_path, "rb") as f:
    data = pickle.load(f)


image = cv2.imread(args["image"])
rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)


print("[INFO] Recognizing faces...")
boxes = face_recognition.face_locations(rgb, model="hog")
encodings = face_recognition.face_encodings(rgb, boxes)

names = []

for encoding in encodings:
    matches = face_recognition.compare_faces(data["encodings"], encoding)
    name = "Unknown"

    if True in matches:
        matchedIdxs = [i for (i, b) in enumerate(matches) if b]
        counts = {}

        for i in matchedIdxs:
            name = data["names"][i]
            counts[name] = counts.get(name, 0) + 1

        name = max(counts, key=counts.get)

    names.append(name)


for (top, right, bottom, left), name in zip(boxes, names):
    cv2.rectangle(image, (left, top), (right, bottom), (0, 255, 0), 2)
    y = top - 15 if top - 15 > 15 else top + 15
    cv2.putText(image, name, (left, y), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 255, 0), 2)

cv2.imshow("Image", image)
cv2.waitKey(0)
