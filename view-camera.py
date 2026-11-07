"""Live view of a Hiwonder TonyPi's USB camera in your web browser. Read only.

    python3 view-camera.py --host 192.168.149.1 --user pi --key ~/.ssh/id_ed25519
    then open http://localhost:8099/ ; stop with Ctrl+C.

It starts `ssh` to the robot and sends it ONE script, stream-camera.py, which only reads the camera. Frames come back over the same
ssh link and are served as motion JPEG on this computer only (127.0.0.1). Nothing new listens on the robot, and nothing here can
move it. If the stream drops it reconnects every 2 seconds. Needs key-based ssh to the robot, python3 with OpenCV (cv2) on the
robot, and python3 on this computer; no other packages.
"""

import argparse
import struct
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "stream-camera.py"

latest = {"jpg": None, "n": 0, "t": 0.0, "error": ""}
cond = threading.Condition()

PAGE = b"""<!doctype html><meta charset=utf-8><title>TonyPi camera</title>
<body style="margin:0;background:#111;color:#ccc;font:14px sans-serif">
<img src="/stream" style="display:block;max-width:100%;height:auto;margin:auto">
<p style="text-align:center">live from the robot (read only) - <a href="/frame" style="color:#8cf">single frame</a></p>"""


def read_exact(stream, n):
    data = b""
    while len(data) < n:
        chunk = stream.read(n - len(data))
        if not chunk:
            return None
        data += chunk
    return data


def pump(target, key):
    cmd = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", "-o", "ServerAliveInterval=5", "-o", "ServerAliveCountMax=2"]
    if key:
        cmd += ["-i", str(Path(key).expanduser()), "-o", "IdentitiesOnly=yes"]
    cmd += [target, "python3", "-"]
    while True:
        proc = None
        try:
            proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            proc.stdin.write(SCRIPT.read_bytes())
            proc.stdin.close()
            while True:
                head = read_exact(proc.stdout, 4)
                if head is None:
                    break
                (length,) = struct.unpack(">I", head)
                jpg = read_exact(proc.stdout, length)
                if jpg is None:
                    break
                with cond:
                    latest.update(jpg=jpg, n=latest["n"] + 1, t=time.time(), error="")
                    cond.notify_all()
            err = proc.stderr.read().decode("utf-8", "replace").strip().splitlines()
            latest["error"] = err[-1][:160] if err else "stream ended"
        except Exception as error:  # robot off, out of reach, ...
            latest["error"] = str(error)[:160]
        finally:
            if proc and proc.poll() is None:
                proc.terminate()
        print("camera stream stopped:", latest["error"], "- retrying in 2 s", file=sys.stderr, flush=True)
        time.sleep(2.0)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        if self.path == "/stream":
            self.send_response(200)
            self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            seen = -1
            try:
                while True:
                    with cond:
                        cond.wait_for(lambda: latest["n"] != seen, timeout=5.0)
                        jpg, seen = latest["jpg"], latest["n"]
                    if jpg is None:
                        continue
                    self.wfile.write(b"--frame\r\nContent-Type: image/jpeg\r\nContent-Length: %d\r\n\r\n" % len(jpg))
                    self.wfile.write(jpg + b"\r\n")
            except (BrokenPipeError, ConnectionResetError, OSError):
                return
        elif self.path == "/frame":
            jpg = latest["jpg"]
            if jpg is None:
                self.send_error(503, "no frame yet: " + latest["error"])
                return
            self.send_response(200)
            self.send_header("Content-Type", "image/jpeg")
            self.send_header("Content-Length", str(len(jpg)))
            self.end_headers()
            self.wfile.write(jpg)
        elif self.path in ("/", "/index.html"):
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.send_header("Content-Length", str(len(PAGE)))
            self.end_headers()
            self.wfile.write(PAGE)
        else:
            self.send_error(404)


def main():
    parser = argparse.ArgumentParser(description="Live, read-only view of a TonyPi's USB camera through ssh.")
    parser.add_argument("--host", default="192.168.149.1", help="robot address (default: the TonyPi's own hotspot)")
    parser.add_argument("--user", default="pi", help="ssh user on the robot")
    parser.add_argument("--key", default="", help="ssh private key (default: whatever ssh would use)")
    parser.add_argument("--port", type=int, default=8099, help="local port for the viewer")
    args = parser.parse_args()
    threading.Thread(target=pump, args=(f"{args.user}@{args.host}", args.key), daemon=True).start()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    server.daemon_threads = True
    print(f"live view: http://localhost:{args.port}/   (Ctrl+C to stop)", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
