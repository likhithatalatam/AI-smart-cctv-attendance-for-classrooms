# encode_faces.py
import os
import cv2
import face_recognition
import pickle
import argparse


def encode_faces(dataset_path, encodings_path):
    known_encodings = []
    known_rollnos = []

    for person_name in os.listdir(dataset_path):
        person_dir = os.path.join(dataset_path, person_name)
        if not os.path.isdir(person_dir):
            continue

        print(f"[INFO] Processing person: {person_name}")

        for img_file in os.listdir(person_dir):
            img_path = os.path.join(person_dir, img_file)

            try:
                image = cv2.imread(img_path)
                if image is None:
                    print(f"[WARNING] Could not read {img_path}")
                    continue
                rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

                boxes = face_recognition.face_locations(rgb, model="hog")
                if len(boxes) == 0:
                    print(f"[WARNING] No face found in {img_file}")
                    continue

                encodings = face_recognition.face_encodings(rgb, boxes)
                known_encodings.append(encodings[0])
                known_rollnos.append(person_name)

            except Exception as e:
                print(f"[ERROR] Failed processing {img_file}: {e}")

    print(f"[INFO] Serializing encodings to {encodings_path}...")
    data = {"encodings": known_encodings, "names": known_rollnos}
    with open(encodings_path, "wb") as f:
        pickle.dump(data, f)

    print("[INFO] Encoding completed successfully!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-d", "--dataset", required=True, help="path to input dataset of faces"
    )
    parser.add_argument(
        "-e",
        "--encodings",
        required=True,
        help="path to serialized db of facial encodings",
    )
    args = parser.parse_args()

    encode_faces(args.dataset, args.encodings)
