"""READ-ONLY: stream a TonyPi's USB camera as JPEG frames to stdout. Run ON the robot, through ssh (view-camera.py does this):

    ssh pi@<robot> python3 - < stream-camera.py

Each frame is a 4-byte big-endian length followed by that many JPEG bytes. It opens /dev/video0 (640x480), skips the first 30 frames
so the exposure settles, then sends frames until the other end closes the pipe. It does not touch the servos, the servo bus or the
stock program's vision functions, and it opens no port on the robot. If the camera is busy it says so on stderr and exits.
"""

import struct
import sys

import cv2

QUALITY = 70
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    sys.stderr.write("cannot open /dev/video0 (busy or missing)\n")
    sys.exit(1)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
for _ in range(30):
    cap.read()
try:
    while True:
        ok, frame = cap.read()
        if not ok:
            continue
        ok, jpg = cv2.imencode(".jpg", frame, (int(cv2.IMWRITE_JPEG_QUALITY), QUALITY))
        data = jpg.tobytes()
        sys.stdout.buffer.write(struct.pack(">I", len(data)) + data)
        sys.stdout.buffer.flush()
except (BrokenPipeError, KeyboardInterrupt):
    pass
finally:
    cap.release()
