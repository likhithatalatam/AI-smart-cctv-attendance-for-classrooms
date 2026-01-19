import face_recognition
import imutils
import pickle
import time
import cv2
import argparse

# construct the argument parser
ap = argparse.ArgumentParser()
ap.add_argument("-e", "--encodings", required=True,
    help="path to serialized db of facial encodings")
ap.add_argument("-d", "--detection-method", type=str, default="hog",
    help="face detection model to use: either 'hog' or 'cnn'")
ap.add_argument("-t", "--tolerance", type=float, default=0.45,
    help="tolerance for face comparison (lower = stricter, default=0.45)")
args = vars(ap.parse_args())

# load the known faces and embeddings
print("[INFO] loading encodings...")
data = pickle.loads(open(args["encodings"], "rb").read())

# initialize the video stream
print("[INFO] starting video stream...")
vs = cv2.VideoCapture(0)
time.sleep(2.0)

while True:
    ret, frame = vs.read()
    if not ret:
        break

    # resize frame for speed
    frame = imutils.resize(frame, width=500)
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    # detect faces
    boxes = face_recognition.face_locations(rgb, model=args["detection_method"])
    encodings = face_recognition.face_encodings(rgb, boxes)

    names = []

    for encoding in encodings:
        distances = face_recognition.face_distance(data["encodings"], encoding)
        min_distance = min(distances) if len(distances) > 0 else 1.0

        if min_distance < args["tolerance"]:
            idx = distances.tolist().index(min_distance)
            name = data["names"][idx]
            confidence = 1 - min_distance  # higher = better
            name = f"{name} ({confidence:.2f})"
        else:
            name = "Unknown"

        names.append(name)

    # draw results
    for ((top, right, bottom, left), name) in zip(boxes, names):
        cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)
        y = top - 15 if top - 15 > 15 else top + 15
        cv2.putText(frame, name, (left, y),
            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

    cv2.imshow("Face Recognition", frame)
    key = cv2.waitKey(1) & 0xFF

    if key == ord("q"):
        break

vs.release()
cv2.destroyAllWindows()
