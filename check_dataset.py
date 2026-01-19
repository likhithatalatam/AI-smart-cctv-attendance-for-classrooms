import os
import cv2
import face_recognition

# Path to your dataset folder
dataset_path = "dataset"

# Supported image formats
supported_ext = (".jpg", ".jpeg", ".png")

print(f"Checking dataset in folder: {dataset_path}\n")

# Loop through each person's folder
for person_name in os.listdir(dataset_path):
    person_path = os.path.join(dataset_path, person_name)
    if not os.path.isdir(person_path):
        continue

    images = [f for f in os.listdir(person_path) if f.lower().endswith(supported_ext)]
    
    if not images:
        print(f"[WARNING] No images found in folder: {person_name}")
        continue

    for img_name in images:
        img_path = os.path.join(person_path, img_name)
        image = cv2.imread(img_path)
        if image is None:
            print(f"[WARNING] Cannot read image: {img_path}")
            continue

        # Detect faces in the image
        face_locations = face_recognition.face_locations(image)
        if len(face_locations) == 0:
            print(f"[WARNING] No face detected in image: {img_path}")
        else:
            print(f"[OK] Face detected in image: {img_path}")

print("\nDataset check complete!")
