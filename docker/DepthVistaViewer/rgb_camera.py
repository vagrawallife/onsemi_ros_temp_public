"""
rgb_camera.py - detect/open an EXTERNAL USB RGB camera (prefer e-con VID 2560),
never the laptop webcam by default. Cross-platform (Windows pygrabber + Linux
sysfs).

JETSON/V4L2 FIX: you cannot resize a live UVC stream on Linux - doing so yields
malformed/empty frames that crash cv2.resize (-215). set_resolution() now
RELEASES + REOPENS the device at the new size. read() rejects empty frames so a
bad frame can never reach cv2.resize. There is NO cv2.resize in this file, so any
-215 in rgb_camera means an OLD copy is still deployed (rebuild image / mount).
"""

import os
import sys
import glob
from time import time
import cv2

__version__ = "rgb_camera v2.0 (jetson-safe resize + VID detect)"
print(f"[rgb_camera] loaded: {__version__}")

ECON_VID = "2560"
KNOWN_MODULE_KEYWORDS = ["see3cam", "e-con", "econ", "ar0234", "24cug", "cu13",
                         "cu20", "cu135", "sturdecam", "hyperyon", "nilecam"]
WEBCAM_NAME_KEYWORDS = ["integrated", "built-in", "built in", "hd webcam",
                        "webcam", "facetime", "front", "internal", "microsoft",
                        "surface", "chicony", "quanta", "sunplus", "realtek",
                        "azurewave", "ir camera", "infrared"]
WEBCAM_VIDS = {"04f2", "0408", "5986", "0bda", "13d3", "1bcf", "04ca", "064e",
               "30c9", "0c45"}
FALLBACK_RES = [(1280, 960), (1600, 1200), (1920, 1200), (1280, 720), (640, 480)]
HIGHRES_HINTS = [(1600, 1200), (1920, 1200), (1280, 960)]


def _backend():
    return cv2.CAP_DSHOW if sys.platform == "win32" else 0


def _linux_info():
    info = {}
    for path in sorted(glob.glob("/sys/class/video4linux/video*")):
        try:
            idx = int(os.path.basename(path).replace("video", ""))
        except ValueError:
            continue
        entry = {"name": "", "vid": "", "pid": "", "usb": False}
        try:
            with open(os.path.join(path, "name")) as f:
                entry["name"] = f.read().strip()
        except Exception:
            pass
        try:
            dev = os.path.realpath(os.path.join(path, "device"))
            d = dev
            for _ in range(6):
                idv = os.path.join(d, "idVendor")
                if os.path.isfile(idv):
                    with open(idv) as f:
                        entry["vid"] = f.read().strip().lower()
                    idp = os.path.join(d, "idProduct")
                    if os.path.isfile(idp):
                        with open(idp) as f:
                            entry["pid"] = f.read().strip().lower()
                    entry["usb"] = True
                    break
                d = os.path.dirname(d)
        except Exception:
            pass
        info[idx] = entry
    return info


def _windows_info():
    out = {}
    try:
        from pygrabber.dshow_graph import FilterGraph
        g = FilterGraph()
        names = g.get_input_devices()
        try:
            paths = g.get_input_devices_with_details()
        except Exception:
            paths = []
        for i, name in enumerate(names):
            vid = pid = ""; usb = False
            src = (str(paths[i]).lower() if i < len(paths) else "") + " " + name.lower()
            if "vid_" in src:
                try:
                    vid = src.split("vid_", 1)[1][:4].lower(); usb = True
                except Exception:
                    pass
            if "pid_" in src:
                try:
                    pid = src.split("pid_", 1)[1][:4].lower()
                except Exception:
                    pass
            out[i] = {"name": name, "vid": vid, "pid": pid, "usb": usb}
    except Exception:
        pass
    return out


def device_info():
    return _windows_info() if sys.platform == "win32" else _linux_info()


def _score(entry, cap=None):
    name = (entry.get("name") or "").lower()
    vid = (entry.get("vid") or "").lower()
    s = 0
    if vid == ECON_VID:
        s += 200
    if any(k in name for k in KNOWN_MODULE_KEYWORDS):
        s += 100
    if any(k in name for k in WEBCAM_NAME_KEYWORDS):
        s -= 100
    if vid in WEBCAM_VIDS:
        s -= 100
    if entry.get("usb") and vid and vid != ECON_VID and vid not in WEBCAM_VIDS and s >= 0:
        s += 40
    if s == 0 and cap is not None:
        for (w, h) in HIGHRES_HINTS:
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, w)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, h)
            if int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) == w and \
               int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) == h:
                s += 20
                break
    return s


def probe(max_index=8, exclude_indices=None):
    exclude = set(exclude_indices or [])
    info = device_info()
    found = []
    for i in range(max_index):
        if i in exclude:
            continue
        cap = cv2.VideoCapture(i, _backend())
        if not cap.isOpened():
            cap = cv2.VideoCapture(i)
        if not cap.isOpened():
            cap.release(); continue
        ok, frame = cap.read()
        if not ok or frame is None or getattr(frame, "size", 0) == 0:
            cap.release(); continue
        entry = info.get(i, {"name": "", "vid": "", "pid": "", "usb": False})
        score = _score(entry, cap)
        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or frame.shape[1]
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or frame.shape[0]
        found.append({"index": i, "name": entry.get("name") or f"Camera {i}",
                      "vid": entry.get("vid", ""), "pid": entry.get("pid", ""),
                      "usb": entry.get("usb", False),
                      "width": w, "height": h, "score": score})
        cap.release()
    found.sort(key=lambda d: (-d["score"], d["index"]))
    return found


def pick_rgb_index(exclude_indices=None, allow_webcam=False):
    cams = probe(exclude_indices=exclude_indices)
    if not cams:
        return None
    for c in cams:
        if c["score"] >= 0:
            return c["index"]
    return cams[0]["index"] if allow_webcam else None


def pick_econ_index(exclude_indices=None):
    return pick_rgb_index(exclude_indices=exclude_indices)


class RGBCamera:
    def __init__(self):
        self.cap = None
        self.index = None
        self.name = ""
        self.vid = ""
        self.width = 0
        self.height = 0
        self._fourcc = "MJPG"

    def _try_open(self, index, w, h, fourcc):
        cap = cv2.VideoCapture(index, _backend())
        if not cap.isOpened():
            cap = cv2.VideoCapture(index)
        if not cap.isOpened():
            return None
        if fourcc:
            try:
                cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*fourcc))
            except Exception:
                pass
        if w and h:
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, int(w))
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, int(h))
        try:
            ok, frame = cap.read()
            if not ok or frame is None or getattr(frame, "size", 0) == 0:
                cap.release(); return None
            return cap
        except cv2.error:
            return None
        

    def open(self, index=None, width=None, height=None, fourcc="MJPG",
             exclude_indices=None, allow_webcam=False):
        self.close()
        self._fourcc = fourcc
        info = device_info()
        if index is None:
            index = pick_rgb_index(exclude_indices=exclude_indices,
                                   allow_webcam=allow_webcam)
        if index is None:
            return False
        tries = []
        if width and height:
            tries.append((int(width), int(height)))
        tries += [r for r in FALLBACK_RES if r not in tries]
        tries.append((0, 0))
        for (w, h) in tries:
            cap = self._try_open(index, w, h, fourcc)
            if cap is not None:
                self.cap = cap
                self.index = index
                e = info.get(index, {})
                self.name = e.get("name") or f"Camera {index}"
                self.vid = e.get("vid", "")
                self.width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                self.height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                vtag = f" VID:{self.vid}" if self.vid else ""
                print(f"RGB camera opened: [{index}] '{self.name}'{vtag} at "
                      f"{self.width}x{self.height} (requested {w}x{h})")
                return True
        return False

    def set_resolution(self, width, height):
        """Release + REOPEN at the new resolution (Jetson/V4L2-safe). Never
        touches a live stream. Returns True if the new size matches the request."""
        if self.cap is None or self.index is None:
            return False
        idx = self.index
        try:
            self.cap.release()
        except Exception:
            pass
        self.cap = None
        for (w, h) in [(int(width), int(height))] + FALLBACK_RES + [(0, 0)]:
            cap = self._try_open(idx, w, h, self._fourcc)
            if cap is not None:
                self.cap = cap
                self.width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                self.height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                print(f"RGB resolution set to {self.width}x{self.height} "
                      f"(requested {width}x{height})")
                return (self.width, self.height) == (int(width), int(height))
        return False
    def read(self):
        """Valid BGR frame or None (guards against empty/tiny frames)."""
        if self.cap is None:
            return None
        try:
            ok, frame = self.cap.read()
        except cv2.error:
            return None
        if not ok or frame is None:
            return None
        if getattr(frame, "size", 0) == 0 or frame.shape[0] < 2 or frame.shape[1] < 2:
            return None
        return frame

    def is_open(self):
        return self.cap is not None

    def close(self):
        if self.cap is not None:
            try:
                self.cap.release()
            except Exception:
                pass
        self.cap = None
        self.index = None
        self.name = ""
        self.vid = ""
        self.width = self.height = 0


if __name__ == "__main__":
    print(f"Platform: {sys.platform}   (e-con VID = {ECON_VID})")
    cams = probe()
    if not cams:
        print("No working cameras detected.")
    else:
        print("\nDetected cameras (best first):")
        for c in cams:
            if c["vid"] == ECON_VID:
                tag = "  <== e-con (VID 2560)"
            elif c["score"] >= 100:
                tag = "  <== known module (by name)"
            elif c["score"] < 0:
                tag = "  (integrated webcam - excluded)"
            elif c["usb"]:
                tag = "  (external USB)"
            else:
                tag = ""
            print(f"  [{c['index']}] {c['name']}  {c['width']}x{c['height']}"
                  f"  vid={c['vid'] or '?'}  score={c['score']}{tag}")
    print("\nAuto-picked RGB index (webcam excluded):", pick_rgb_index())
