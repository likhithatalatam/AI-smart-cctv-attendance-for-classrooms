import cv2
import face_recognition
import pickle
import requests
import time

# ---------------- CONFIG ----------------
API_URL = "http://127.0.0.1:5000/api/attendance/mark"
ENCODINGS_FILE = "encodings.pickle"
CAMERA_ID = "laptop-cam"
CONFIDENCE = 0.92

# ----------------------------------------

print("Loading face encodings...")
with open(ENCODINGS_FILE, "rb") as f:
    data = pickle.load(f)

known_encodings = data["encodings"]
known_rollnos = data["names"]

print(f"Loaded {len(known_rollnos)} registered students")

cap = cv2.VideoCapture(0)
marked_today = set()  # avoid spamming same student

print("Live Multi-Face Attendance Started (Press Q to stop)")

while True:
    ret, frame = cap.read()
    if not ret:
        break

    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    # detect all faces
    face_locations = face_recognition.face_locations(rgb)
    face_encodings = face_recognition.face_encodings(rgb, face_locations)

    for encoding, location in zip(face_encodings, face_locations):
        matches = face_recognition.compare_faces(
            known_encodings, encoding, tolerance=0.45
        )

        name = "Unknown"

        if True in matches:
            matched_idxs = [i for i, m in enumerate(matches) if m]
            counts = {}

            for i in matched_idxs:
                roll = known_rollnos[i]
                counts[roll] = counts.get(roll, 0) + 1

            name = max(counts, key=counts.get)

            # MARK ATTENDANCE ONLY ONCE
            if name not in marked_today:
                payload = {
                    "recognized_id": name,
                    "confidence": CONFIDENCE,
                    "camera_id": CAMERA_ID,
                }

                try:
                    r = requests.post(API_URL, json=payload)
                    print(f"Attendance marked for {name} → {r.status_code}")
                    marked_today.add(name)
                except Exception as e:
                    print("API Error:", e)

        # draw box + label
        top, right, bottom, left = location
        color = (0, 255, 0) if name != "Unknown" else (0, 0, 255)

        cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
        cv2.putText(
            frame, name, (left, top - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.75, color, 2
        )

    cv2.imshow("Live Attendance - Multi Face", frame)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()
