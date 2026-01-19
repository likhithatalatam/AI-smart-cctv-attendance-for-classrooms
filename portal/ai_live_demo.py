import cv2
import requests
import time

API_URL = "http://127.0.0.1:5000/api/attendance/mark"

ROLL_NO = "226K1A05B8"  # 👈 use a real roll no from DB

cap = cv2.VideoCapture(0)

last_sent = 0

print("🎥 Live attendance demo started (Press Q to stop)")

while True:
    ret, frame = cap.read()
    if not ret:
        break

    cv2.imshow("Live Camera - Attendance Demo", frame)

    # Send attendance every 10 seconds (avoid spam)
    if time.time() - last_sent > 10:
        payload = {
            "recognized_id": ROLL_NO,
            "confidence": 0.95,
            "camera_id": "laptop-cam",
        }

        try:
            r = requests.post(API_URL, json=payload)
            print("📡 Attendance sent:", r.status_code)
            last_sent = time.time()
        except Exception as e:
            print("❌ Error:", e)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()
