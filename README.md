# tonypi-camera-view

A live, **read-only** view of a [Hiwonder TonyPi](https://www.hiwonder.com/) humanoid robot's USB camera, in your web browser, with no software to install on the robot.

The TonyPi's stock program only serves video while one of its vision functions is running, and those functions can make the robot move. This tool skips that: it opens the camera directly, sends frames over the ssh connection you already have, and shows them on your own computer.

```
robot (stream-camera.py, reads /dev/video0)  --ssh-->  laptop (view-camera.py)  -->  http://localhost:8099/
```

## Safe by design

- Only reads the camera. It never touches the servos, the servo bus or the stock program, and it sends the robot no movement commands.
- Opens **no port on the robot**. The one script that runs there is piped over ssh and leaves nothing behind.
- The viewer listens on `127.0.0.1` only, so nobody else on your network can see the picture.

## Use

You need key-based ssh to the robot (the user `pi`), Python 3 on your computer, and OpenCV (`cv2`) for Python 3 on the robot (the TonyPi image already has it).

```
python3 view-camera.py --host 192.168.149.1 --user pi --key ~/.ssh/id_ed25519
```

Open <http://localhost:8099/>. `http://localhost:8099/frame` gives a single still. The defaults match the robot's own Wi-Fi hotspot (`192.168.149.1`). If the stream drops, the viewer retries every 2 seconds. Options: `--host`, `--user`, `--key`, `--port`.

To grab frames by hand instead: `ssh pi@<robot> python3 - < stream-camera.py` sends each frame as a 4-byte big-endian length followed by that many JPEG bytes.

## Notes from a real robot

- The camera on the tested kit was a generic "USB 2.0 PC Cam" (Silicon Motion SM371) at `/dev/video0`, 640x480.
- If every picture is a dark smear, check that the lens barrel is **screwed in all the way**. That was the cause here. A thin line that never moves in the picture is a hair on the sensor side of the lens.
- A bright light or screen in a dark room blows out to white with coloured fringes. Judge the picture in even room light.

## Credit

Created by [agamemnon4700](https://github.com/agamemnon4700), built together with Claude (Anthropic) as an AI coding assistant. Released under the MIT licence (see `LICENSE`).
