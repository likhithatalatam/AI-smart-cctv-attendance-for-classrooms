import os
import pickle
import face_recognition

ENCODINGS_PATH = os.path.join(
    os.path.dirname(__file__), "..", "recognizer", "encodings.pickle"
)


def update_encodings(roll_no, image_paths):
    encodings = []
    roll_nos = []

    # Load existing encodings if file exists
    if os.path.exists(ENCODINGS_PATH):
        with open(ENCODINGS_PATH, "rb") as f:
            data = pickle.load(f)
            encodings = data["encodings"]
            roll_nos = data["roll_nos"]

    for img_path in image_paths:
        image = face_recognition.load_image_file(img_path)
        face_encs = face_recognition.face_encodings(image)

        if len(face_encs) == 0:
            continue

        encodings.append(face_encs[0])
        roll_nos.append(roll_no)

    with open(ENCODINGS_PATH, "wb") as f:
        pickle.dump({"encodings": encodings, "roll_nos": roll_nos}, f)

    print(f"✅ Encoding updated for {roll_no}")
