#!/usr/bin/env python3
"""
rgb_viewer.py - STANDALONE RGB camera viewer (self-contained).

Fixes vs the previous version:
  1) No error spam - we ONLY probe indices that actually exist (from device
     enumeration), suppress OpenCV's internal logger, and avoid the noisy
     double-open + obsensor backend.
  2) Good image - we force a real backend + MJPG; and if the camera streams a
     raw packed format (UYVY/YUYV), we convert it to BGR ourselves so it never
     shows a garbled / mis-strided picture.
  3) No multi-view tiling - that artifact is a wrong-stride raw frame; handled by
     the explicit YUV->BGR conversion + validating the buffer size.

Run:
    python rgb_viewer.py
    python rgb_viewer.py --device 1
    python rgb_viewer.py --list          # cameras + real supported resolutions
    python rgb_viewer.py --backend msmf   # try Media Foundation on Windows
    python rgb_viewer.py --gst            # GStreamer pipeline (best on Jetson)
"""

import os
import re
import sys
import glob
import base64
import argparse
import subprocess

# Quiet OpenCV's internal logging BEFORE importing cv2 (kills the WARN/ERROR spam)
os.environ.setdefault("OPENCV_LOG_LEVEL", "FATAL")
os.environ.setdefault("OPENCV_VIDEOIO_PRIORITY_MSMF", "0")   # avoid obsensor probing

import cv2
import numpy as np
try:
    cv2.utils.logging.setLogLevel(cv2.utils.logging.LOG_LEVEL_SILENT)
except Exception:
    pass

ECON_VID = "2560"
KNOWN = ["see3cam", "e-con", "econ", "ar0234", "24cug", "cu13", "cu20", "sturdecam"]
# ONLY clearly-INTEGRATED webcam indicators (do NOT include the generic word
# "webcam" - many legit external USB cameras have "webcam" in their name).
WEBCAM = ["integrated", "built-in", "built in", "facetime", "front camera",
          "internal", "ir camera", "infrared"]
WEBCAM_VIDS = {"04f2", "0408", "5986", "0bda", "13d3", "1bcf", "04ca", "064e",
               "30c9", "0c45"}
COMMON_RES = [(640, 480), (800, 600), (1280, 720), (1280, 960),
              (1600, 1200), (1920, 1080), (1920, 1200)]


def _is_win():
    return sys.platform == "win32"


def _backend(name=None):
    if name == "msmf" and _is_win():
        return cv2.CAP_MSMF
    if name == "dshow" and _is_win():
        return cv2.CAP_DSHOW
    if name == "v4l2" and not _is_win():
        return getattr(cv2, "CAP_V4L2", 0)
    # defaults
    if _is_win():
        return cv2.CAP_DSHOW
    return getattr(cv2, "CAP_V4L2", 0)


# ---------------- device enumeration (only real indices) ----------------
def _linux_info():
    info = {}
    for path in sorted(glob.glob("/sys/class/video4linux/video*")):
        try:
            idx = int(os.path.basename(path).replace("video", ""))
        except ValueError:
            continue
        e = {"name": "", "vid": "", "usb": False, "node": f"/dev/video{idx}"}
        try:
            with open(os.path.join(path, "name")) as f:
                e["name"] = f.read().strip()
        except Exception:
            pass
        try:
            d = os.path.realpath(os.path.join(path, "device"))
            for _ in range(6):
                iv = os.path.join(d, "idVendor")
                if os.path.isfile(iv):
                    with open(iv) as f:
                        e["vid"] = f.read().strip().lower()
                    e["usb"] = True
                    break
                d = os.path.dirname(d)
        except Exception:
            pass
        info[idx] = e
    return info


def _win_info():
    out = {}
    try:
        from pygrabber.dshow_graph import FilterGraph
        for i, n in enumerate(FilterGraph().get_input_devices()):
            vid = ""
            s = n.lower()
            if "vid_" in s:
                try:
                    vid = s.split("vid_", 1)[1][:4].lower()
                except Exception:
                    pass
            out[i] = {"name": n, "vid": vid, "usb": ("vid_" in s), "node": str(i)}
    except Exception:
        pass
    return out


def device_info():
    return _win_info() if _is_win() else _linux_info()


def _score(e):
    """
    Camera-AGNOSTIC scoring: we do NOT prefer any particular brand/model. The
    only thing we actively avoid is the built-in laptop WEBCAM. Any external
    USB/UVC camera (e-con or otherwise) is treated equally as a valid choice.

      -100 : looks like an integrated webcam (name or known webcam VID)
       +50 : external USB camera with a real VID (any brand)
       +10 : e-con VID/name -> a tiny nudge ONLY to break ties when multiple
             external cameras are present (never enough to hide another camera)
        0  : unknown
    """
    name = (e.get("name") or "").lower()
    vid = (e.get("vid") or "").lower()
    s = 0
    # exclude the laptop webcam
    if any(k in name for k in WEBCAM):
        s -= 100
    if vid in WEBCAM_VIDS:
        s -= 100
    # any external USB camera is a valid pick (brand-agnostic)
    if e.get("usb") and vid and vid not in WEBCAM_VIDS:
        s += 50
    # tiny tie-breaker nudge for e-con (does NOT suppress other cameras)
    if s >= 0 and (vid == ECON_VID or any(k in name for k in KNOWN)):
        s += 10
    return s


def supported_resolutions(index, info_entry):
    res = []
    if not _is_win():
        node = (info_entry or {}).get("node", f"/dev/video{index}")
        try:
            out = subprocess.check_output(
                ["v4l2-ctl", "--list-formats-ext", "-d", node],
                stderr=subprocess.DEVNULL, text=True, timeout=4)
            for m in re.finditer(r"Size:\s*Discrete\s+(\d+)x(\d+)", out):
                wh = (int(m.group(1)), int(m.group(2)))
                if wh not in res:
                    res.append(wh)
        except Exception:
            pass
    else:
        try:
            from pygrabber.dshow_graph import FilterGraph
            g = FilterGraph()
            g.add_video_input_device(index)
            try:
                for f in g.get_formats():
                    wh = (int(f["width"]), int(f["height"]))
                    if wh not in res:
                        res.append(wh)
            finally:
                g.remove_filters()
        except Exception:
            pass
    if not res:
        res = list(COMMON_RES)
    res.sort()
    return res


def probe(backend_name=None):
    """Probe ONLY the indices that device enumeration reports (no blind 0..7)."""
    info = device_info()
    indices = sorted(info.keys()) if info else list(range(4))
    be = _backend(backend_name)
    found = []
    for i in indices:
        cap = cv2.VideoCapture(i, be)
        if not cap.isOpened():
            cap.release(); continue
        ok, fr = cap.read()
        if not ok or fr is None or getattr(fr, "size", 0) == 0:
            cap.release(); continue
        e = info.get(i, {"name": f"Camera {i}", "vid": "", "usb": False})
        found.append({"index": i, "name": e.get("name") or f"Camera {i}",
                      "vid": e.get("vid", ""), "score": _score(e),
                      "width": int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                      "height": int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))})
        cap.release()
    found.sort(key=lambda d: (-d["score"], d["index"]))
    return found


def pick_index(backend_name=None, allow_webcam=False):
    cams = probe(backend_name)
    for c in cams:
        if c["score"] >= 0:
            return c["index"]
    return cams[0]["index"] if (cams and allow_webcam) else None


# ---------------- reliable capture + correct decoding ----------------
def _fourcc_str(cap):
    v = int(cap.get(cv2.CAP_PROP_FOURCC))
    return "".join([chr((v >> (8 * k)) & 0xFF) for k in range(4)]).strip()


def open_capture(index, width, height, backend_name=None, use_gst=False):
    """
    Returns (cap, actual_w, actual_h, fourcc). FOURCC is set BEFORE size.
    On Jetson, use_gst builds a GStreamer pipeline (most reliable).
    """
    if use_gst and not _is_win():
        node = f"/dev/video{index}"
        for cap_type in ("image/jpeg", "video/x-raw"):
            if cap_type == "image/jpeg":
                pipe = (f"v4l2src device={node} ! image/jpeg,width={width},"
                        f"height={height} ! jpegdec ! videoconvert ! appsink")
            else:
                pipe = (f"v4l2src device={node} ! video/x-raw,width={width},"
                        f"height={height} ! videoconvert ! appsink")
            cap = cv2.VideoCapture(pipe, cv2.CAP_GSTREAMER)
            if cap.isOpened():
                ok, fr = cap.read()
                if ok and fr is not None and fr.size:
                    return cap, fr.shape[1], fr.shape[0], "GST"
            cap.release()

    # Different resolutions live under different FOURCCs on e-con cameras
    # (e.g. 640x480 may exist ONLY in YUYV, while 1280x960 is MJPG). So we TRY a
    # list of FOURCCs at the requested size and keep the one that ACHIEVES the
    # EXACT resolution. Order: MJPG (high-res/bandwidth), then YUYV/YUY2 (common
    # for VGA), then leave the FOURCC untouched (camera default).
    be = _backend(backend_name)
    fourcc_candidates = ["MJPG", "YUYV", "YUY2", None]
    best = None                                   # (cap, aw, ah, cc, exact)

    def _try_fourcc(fcc):
        cap = cv2.VideoCapture(index, be)
        if not cap.isOpened():
            return None
        if fcc is not None:
            try:
                cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*fcc))
            except Exception:
                pass
        if width and height:
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, int(width))
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, int(height))
        try:
            cap.set(cv2.CAP_PROP_CONVERT_RGB, 1)
        except Exception:
            pass
        aw = ah = 0
        for _ in range(6):                        # warm up so the mode applies
            ok, fr = cap.read()
            if ok and fr is not None and fr.size:
                ah, aw = fr.shape[0], fr.shape[1]
        if aw == 0:
            cap.release()
            return None
        return cap, aw, ah, _fourcc_str(cap)

    for fcc in fourcc_candidates:
        r = _try_fourcc(fcc)
        if r is None:
            continue
        cap, aw, ah, cc = r
        exact = (not width or not height) or (aw == int(width) and ah == int(height))
        if exact:
            # perfect match -> use immediately
            if best is not None:
                best[0].release()
            return cap, aw, ah, cc
        # keep the first working (non-exact) as a fallback, release the rest
        if best is None:
            best = [cap, aw, ah, cc]
        else:
            cap.release()

    if best is not None:
        return best[0], best[1], best[2], best[3]
    return None, 0, 0, ""


def decode_frame(cap, want_w, want_h):
    """
    Read a frame and return a clean BGR image. If OpenCV returns a raw packed
    buffer (2 channels or a flat 1-channel of size w*h*2 = YUYV/UYVY), convert it
    to BGR ourselves - this removes the 'tiled / garbled' artifact.
    """
    ok, fr = cap.read()
    if not ok or fr is None or getattr(fr, "size", 0) == 0:
        return None
    # Normal 3-channel BGR
    if fr.ndim == 3 and fr.shape[2] == 3:
        return fr
    # 3-channel but 4 planes (BGRA)
    if fr.ndim == 3 and fr.shape[2] == 4:
        return cv2.cvtColor(fr, cv2.COLOR_BGRA2BGR)
    # 2-channel packed YUV (H, W, 2) -> UYVY
    if fr.ndim == 3 and fr.shape[2] == 2:
        return cv2.cvtColor(fr, cv2.COLOR_YUV2BGR_UYVY)
    # Flat/1-channel: try to reshape as YUYV (w*h*2) then convert
    flat = fr.reshape(-1)
    n = flat.size
    if want_w and want_h and n == want_w * want_h * 2:
        yuv = flat.reshape(want_h, want_w, 2)
        try:
            return cv2.cvtColor(yuv, cv2.COLOR_YUV2BGR_YUYV)
        except Exception:
            return cv2.cvtColor(yuv, cv2.COLOR_YUV2BGR_UYVY)
    # Grayscale
    if fr.ndim == 2:
        return cv2.cvtColor(fr, cv2.COLOR_GRAY2BGR)
    return None


def to_photoimage(tk, bgr):
    if bgr is None or getattr(bgr, "size", 0) == 0:
        return None
    ok, buf = cv2.imencode(".png", bgr)
    if not ok:
        return None
    return tk.PhotoImage(data=base64.b64encode(buf.tobytes()).decode("ascii"))


class RGBViewer:
    def __init__(self, args):
        self.args = args
        self.cap = None
        self.index = None
        self.name = ""
        self.want_w = self.want_h = 0
        self.res_list = list(COMMON_RES)
        self._running = True
        self._imgtk = None
        self._view_w, self._view_h = 900, 640

    def start(self):
        import tkinter as tk
        from tkinter import simpledialog, messagebox
        self.tk = tk; self.simpledialog = simpledialog; self.messagebox = messagebox

        self.root = tk.Tk()
        self.root.title("RGB Camera Viewer")
        self.root.geometry("960x720")
        self.root.configure(bg="#202124")

        self.menubar = tk.Menu(self.root)
        m_cam = tk.Menu(self.menubar, tearoff=0)
        m_cam.add_command(label="Select Device...", command=self.select_device)
        m_cam.add_command(label="Refresh Devices", command=self.refresh_devices)
        m_cam.add_separator()
        m_cam.add_command(label="Exit", command=self.quit)
        self.menubar.add_cascade(label="Camera", menu=m_cam)

        self.var_res = tk.StringVar(value="")
        self.m_res = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="Resolution", menu=self.m_res)

        m_help = tk.Menu(self.menubar, tearoff=0)
        m_help.add_command(label="About", command=lambda: self.messagebox.showinfo(
            "About", "Standalone RGB viewer.\nQuiet probing, MJPG, and raw YUV->BGR "
            "decoding for a clean image.", parent=self.root))
        self.menubar.add_cascade(label="Help", menu=m_help)
        self.root.config(menu=self.menubar)

        self.status = tk.StringVar(value="Opening camera...")
        tk.Label(self.root, textvariable=self.status, anchor="w", fg="#e8eaed",
                 bg="#303134").pack(side="bottom", fill="x")
        self.video = tk.Label(self.root, bg="#202124")
        self.video.pack(side="top", fill="both", expand=True)
        self.video.bind("<Configure>", self._on_resize)
        self.root.protocol("WM_DELETE_WINDOW", self.quit)

        idx = self.args.device if self.args.device >= 0 else pick_index(self.args.backend)
        if idx is None:
            self.status.set("No external RGB camera found. Camera > Select Device...")
        else:
            self._open(idx, self.args.width, self.args.height)

        self.root.after(30, self._tick)
        self.root.mainloop()
        if self.cap is not None:
            self.cap.release()

    def _on_resize(self, e):
        self._view_w = max(2, int(e.width)); self._view_h = max(2, int(e.height))

    def _rebuild_res_menu(self):
        self.m_res.delete(0, "end")
        for (w, h) in self.res_list:
            label = f"{w} x {h}"
            self.m_res.add_radiobutton(label=label, value=label,
                                       variable=self.var_res, command=self._on_resolution)

    def _open(self, index, width=None, height=None):
        if self.cap is not None:
            self.cap.release(); self.cap = None
        info = device_info(); entry = info.get(index, {})
        self.name = entry.get("name") or f"Camera {index}"
        self.res_list = supported_resolutions(index, entry)
        w = width or self.res_list[-1][0]
        h = height or self.res_list[-1][1]
        cap, aw, ah, cc = open_capture(index, w, h, self.args.backend, self.args.gst)
        if cap is None:
            self.status.set(f"Failed to open [{index}] {self.name}"); return
        self.cap = cap; self.index = index; self.want_w, self.want_h = aw, ah
        self._rebuild_res_menu()
        self.var_res.set(f"{aw} x {ah}")
        self.root.title(f"RGB Camera - {self.name}")
        self.status.set(f"[{index}] {self.name}  {aw}x{ah}  {cc}"
                        + (f"  VID:{entry.get('vid','')}" if entry.get('vid') else ""))

    def _on_resolution(self):
        if self.cap is None or self.index is None:
            self.status.set("Open a camera first."); return
        sel = self.var_res.get()
        try:
            w, h = (int(x) for x in sel.lower().split("x"))
        except Exception:
            return
        self.status.set(f"Setting {w}x{h} (reopening)...")
        self.root.update_idletasks()
        self.cap.release(); self.cap = None
        cap, aw, ah, cc = open_capture(self.index, w, h, self.args.backend, self.args.gst)
        if cap is None:
            self.status.set(f"Failed to set {w}x{h}."); return
        self.cap = cap; self.want_w, self.want_h = aw, ah
        self.var_res.set(f"{aw} x {ah}")
        note = "" if (aw, ah) == (w, h) else "  (nearest supported)"
        self.status.set(f"[{self.index}] {self.name}  {aw}x{ah}  {cc}{note}")

    def select_device(self):
        cams = probe(self.args.backend)
        if not cams:
            self.status.set("No cameras detected."); return
        lines = ["Detected cameras (best first):", ""]
        for c in cams:
            tag = "  (webcam)" if c["score"] < 0 else "  (external USB)"
            lines.append(f"[{c['index']}] {c['name']}  {c['width']}x{c['height']}{tag}")
        lines += ["", "Enter index:"]
        val = self.simpledialog.askinteger("Select RGB Device", "\n".join(lines),
                                           initialvalue=cams[0]["index"], minvalue=0,
                                           maxvalue=64, parent=self.root)
        if val is not None:
            self._open(val)

    def refresh_devices(self):
        idx = pick_index(self.args.backend)
        if idx is not None:
            self._open(idx)
        else:
            self.status.set("No external RGB camera found.")

    def _tick(self):
        if not self._running:
            return
        if self.cap is not None:
            frame = decode_frame(self.cap, self.want_w, self.want_h)
            if frame is not None and frame.size:
                h, w = frame.shape[:2]
                fw, fh = self._view_w, self._view_h
                s = min(fw / float(w), fh / float(h)) if (fw > 2 and fh > 2) else 1.0
                nw, nh = max(1, int(w * s)), max(1, int(h * s))
                try:
                    small = cv2.resize(frame, (nw, nh), interpolation=cv2.INTER_AREA)
                    photo = to_photoimage(self.tk, small)
                    if photo is not None:
                        self._imgtk = photo
                        self.video.configure(image=photo)
                except Exception as exc:
                    print("display error:", exc)
        self.root.after(15, self._tick)

    def quit(self):
        self._running = False
        try:
            self.root.quit()
        except Exception:
            pass


def main():
    p = argparse.ArgumentParser(description="Standalone RGB camera viewer.")
    p.add_argument("--device", type=int, default=-1, help="UVC index (-1 = auto-detect)")
    p.add_argument("--width", type=int, default=0, help="initial width (0 = camera max)")
    p.add_argument("--height", type=int, default=0, help="initial height")
    p.add_argument("--backend", choices=["dshow", "msmf", "v4l2"], default=None,
                   help="force a capture backend")
    p.add_argument("--gst", action="store_true", help="use GStreamer (best on Jetson)")
    p.add_argument("--list", action="store_true",
                   help="print detected cameras + supported resolutions and exit")
    args = p.parse_args()

    if args.list:
        info = device_info(); cams = probe(args.backend)
        if not cams:
            print("No cameras detected."); return
        for c in cams:
            e = info.get(c["index"], {})
            print(f"[{c['index']}] {c['name']}  vid={c['vid'] or '?'}  score={c['score']}")
            for (w, h) in supported_resolutions(c["index"], e):
                print(f"      {w}x{h}")
        return

    RGBViewer(args).start()


if __name__ == "__main__":
    main()
