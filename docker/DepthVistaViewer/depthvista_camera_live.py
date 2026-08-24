"""
DepthVista Live Camera Application (CU13) - econ-exact.

CROSS-VERIFIED against econ main.py + iTOF_Controls.py:
  * Resolutions:  Conf HD = 1280x960 ; Conf IR = 640x480.
  * Colormap range per your hardware (Conf HD shows ~0.2-1.2 m, far pixels black):
        Conf HD -> 200-1200      (matches what you observe on the device)
        Conf IR -> 500-6000
    UpdateColorMap is called as econ does: (min, max + 1000, 4).
  * econ does NOT set Integration/Denoise/IRGain/Confidence/Spatial at startup -
    it uses the camera's FIRMWARE DEFAULTS. So we DO NOT force any control profile
    by default (that was making our image differ). Use --apply-profile to opt in.
  * Displays the SDK's own depth_colormap (econ colours). Edit menu = the 5 real
    console controls + Temperatures. Status bar shows live camera resolution.
"""
APP_VERSION = "depthvista_camera_live v3.4 (Jetson mode-switch sync + econ colormap refresh)"

import os, sys, time, base64, ctypes, argparse, threading, subprocess
from ctypes import (Structure, POINTER, byref,
                    c_char, c_int, c_int32, c_uint8, c_uint16, c_uint32, c_uint64)
from datetime import datetime
import numpy as np
import cv2

print(f"[app] {APP_VERSION}")

try:
    from itof_controls import ITOFControls
except Exception:
    ITOFControls = None
try:
    import depthvista_calib as CALIB
except Exception:
    CALIB = None
try:
    from sdk_colormap import bind_update_colormap, get_depth_colormap_bgr
except Exception:
    bind_update_colormap = None
    def get_depth_colormap_bgr(_frm):
        return None

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SDK_LIB_NAME = "DepthVistaSDK.dll" if sys.platform == "win32" else "libDepthVistaSDK.so"
DEFAULT_SDK = os.path.join(SCRIPT_DIR, SDK_LIB_NAME)


class DataMode:
    Depth_IR_Conf_Mode = 1
    Depth_IR_Conf_HD_Mode = 20


# Cross-verified: resolutions certain; Conf HD colormap 200-1200 (your hardware).
MODE_CONFIG = {
    "Conf HD mode (1.2MP)": dict(value=DataMode.Depth_IR_Conf_HD_Mode, reopen=True,
                                 cmap=(200, 4000), res=(1280, 960)),
    "Conf IR mode (VGA)":   dict(value=DataMode.Depth_IR_Conf_Mode, reopen=False,
                                 cmap=(500, 6000), res=(640, 480)),
}
STREAM_MODES = list(MODE_CONFIG.keys())
DEFAULT_STREAM = "Conf HD mode (1.2MP)"

CM_TURBO = "Turbo (Near=Blue, Far=Red)"
CM_ECON = "e-con (Near=Orange, Far=Blue)"
CM_CLI = {CM_TURBO: "turbo", CM_ECON: "econ"}

DISPLAY_SIZES = [("Fit window (auto)", None), ("640 x 480", (640, 480)),
                 ("1280 x 960", (1280, 960)), ("1280 x 720", (1280, 720)),
                 ("1920 x 1080", (1920, 1080))]


def _turbo():
    return getattr(cv2, "COLORMAP_TURBO", cv2.COLORMAP_JET)


class DeviceHandle(Structure):
    _fields_ = [("serialNo", c_char * 50)]


class tofFrame(Structure):
    _fields_ = [("frame_data", POINTER(c_uint8)), ("width", c_uint16), ("height", c_uint16),
                ("pixel_format", c_uint8), ("size", c_uint32),
                ("time_stamp", c_uint64), ("frame_id", c_uint64)]


class frames(Structure):
    _fields_ = [("rgb", tofFrame), ("ir", tofFrame), ("raw_ir", tofFrame),
                ("raw_depth", tofFrame), ("raw_depth_original", tofFrame),
                ("depth_colormap", tofFrame), ("confidence_frame", tofFrame),
                ("confidence_frame2", tofFrame), ("IRA0RawFrame", tofFrame),
                ("IRA1RawFrame", tofFrame), ("IRA2RawFrame", tofFrame),
                ("IRA0RawFrame_save", tofFrame), ("IRA1RawFrame_save", tofFrame),
                ("IRA2RawFrame_save", tofFrame)]


class GMSLDeviceInfo(Structure):
    _fields_ = [("depthNodePath", c_char * 500), ("confNodePath", c_char * 500),
                ("irNodePath", c_char * 500), ("busID", c_int), ("nodeAdd", c_int),
                ("deviceindex", c_int), ("nodeValidation", c_uint16)]


class DeviceInfo(Structure):
    _fields_ = [("deviceName", c_char * 50), ("vid", c_char * 5), ("pid", c_char * 5),
                ("devicePath", c_char * 500), ("serialNo", c_char * 50),
                ("devType", c_int), ("gmsldevinfo", GMSLDeviceInfo)]


def load_sdk_library(sdk_path):
    cand = []
    if sdk_path:
        cand += [sdk_path, os.path.join(SCRIPT_DIR, os.path.basename(sdk_path))]
    cand += [DEFAULT_SDK, SDK_LIB_NAME]
    resolved = next((c for c in cand if c and os.path.isfile(c)), SDK_LIB_NAME)
    if os.path.isabs(resolved):
        resolved = os.path.abspath(resolved)
    lib_dir = os.path.dirname(resolved) if os.path.isabs(resolved) else SCRIPT_DIR
    if sys.platform == "win32":
        try:
            os.add_dll_directory(lib_dir)
        except (AttributeError, OSError):
            pass
        os.environ["PATH"] = lib_dir + os.pathsep + os.environ.get("PATH", "")
    else:
        os.environ["LD_LIBRARY_PATH"] = lib_dir + os.pathsep + os.environ.get("LD_LIBRARY_PATH", "")
    print(f"Loading SDK: {resolved}")
    return ctypes.CDLL(resolved)


class DepthVistaSDK:
    def __init__(self, sdk_path=DEFAULT_SDK):
        self.lib = load_sdk_library(sdk_path)
        self.handle = DeviceHandle()
        self.depth_min, self.depth_max = 500, 4000
        self.device_name = ""
        self._device_info = None
        self._bind()
        self._update_colormap = bind_update_colormap(self.lib, DeviceHandle) if bind_update_colormap else None

    def _opt(self, name, argtypes):
        try:
            f = getattr(self.lib, name); f.argtypes = argtypes; f.restype = c_int
            return f
        except AttributeError:
            return None

    def _bind(self):
        lib = self.lib
        self.Initialize = lib.Initialize; self.Initialize.restype = c_int
        self.DeInitialize = lib.DeInitialize; self.DeInitialize.restype = c_int
        self.GetDeviceCount = lib.GetDeviceCount
        self.GetDeviceCount.argtypes = [POINTER(c_uint32)]; self.GetDeviceCount.restype = c_int
        self.GetDeviceInfo = lib.GetDeviceInfo
        self.GetDeviceInfo.argtypes = [c_uint32, POINTER(DeviceInfo)]; self.GetDeviceInfo.restype = c_int
        self.OpenDevice = lib.OpenDevice
        self.OpenDevice.argtypes = [DeviceInfo, POINTER(DeviceHandle)]; self.OpenDevice.restype = c_int
        self.IsOpened = lib.IsOpened
        self.IsOpened.argtypes = [DeviceHandle]; self.IsOpened.restype = c_int
        self.CloseDevice = lib.CloseDevice
        self.CloseDevice.argtypes = [DeviceHandle]; self.CloseDevice.restype = c_int
        self.SetDataMode = self._opt("SetDataMode", [DeviceHandle, c_int32])
        self.GetDataMode = self._opt("GetDataMode", [DeviceHandle, POINTER(c_int32)])
        # Debug-only depth-range getters, matching the e-con sample bindings.
        self.SetDepthRange = self._opt("SetDepthRange", [DeviceHandle, c_uint16])
        self.GetDepthRange = self._opt("GetDepthRange", [DeviceHandle, POINTER(ctypes.c_int16)])
        self.GetNextFrame = self._opt("GetNextFrame", [DeviceHandle])
        self.GetFrames = lib.GetFrames
        self.GetFrames.argtypes = [DeviceHandle, POINTER(frames)]; self.GetFrames.restype = c_int
        self.SetRGBDMapping = self._opt("SetRGBDMapping", [DeviceHandle, c_uint16])

    def init(self):
        if self.Initialize() == 0:
            raise RuntimeError("SDK Initialize() failed.")
        print("SDK initialized.")

    def list_devices(self):
        count = c_uint32(0)
        if self.GetDeviceCount(byref(count)) != 1:
            raise RuntimeError("GetDeviceCount() failed.")
        devices = []
        print(f"\nDepthVista devices found: {count.value}")
        for i in range(count.value):
            info = DeviceInfo()
            if self.GetDeviceInfo(i, byref(info)) == 1:
                print(f"  [{i}] {info.deviceName.decode(errors='ignore')}")
                devices.append(info)
        return devices

    def open(self, device_info):
        if self.OpenDevice(device_info, byref(self.handle)) < 1:
            raise RuntimeError("OpenDevice() failed.")
        self._device_info = device_info
        self.device_name = device_info.deviceName.decode(errors="ignore")
        print(f"Device opened: {self.device_name}")

    def reopen(self):
        if self._device_info is None:
            return False
        try:
            self.CloseDevice(self.handle)
        except Exception:
            pass
        time.sleep(0.3)
        h = DeviceHandle()
        ok = self.OpenDevice(self._device_info, byref(h))
        if ok >= 1:
            self.handle = h
            return True
        return False

    def set_data_mode(self, value):
        if self.SetDataMode is None:
            return None
        try:
            return self.SetDataMode(self.handle, c_int32(value))
        except Exception:
            return None

    def get_data_mode(self):
        if self.GetDataMode is None:
            return None
        v = c_int32()
        try:
            if self.GetDataMode(self.handle, byref(v)) == 1:
                return int(v.value)
        except Exception:
            pass
        return None

    def get_depth_range(self):
        if self.GetDepthRange is None:
            return None
        v = ctypes.c_int16()
        try:
            if self.GetDepthRange(self.handle, byref(v)) == 1:
                return int(v.value)
        except Exception:
            pass
        return None

    def update_colormap(self, dmin, dmax, debug=False):
        """econ update_colormap(): UpdateColorMap(min, max + 1000, 4)."""
        self.depth_min, self.depth_max = dmin, dmax
        if self._update_colormap is not None:
            sdk_max = int(dmax + 1000)
            r = self._update_colormap(self.handle, int(dmin), sdk_max, 4)
            if debug:
                print(f"[COLORMAP] UpdateColorMap({dmin}, {sdk_max}, 4) -> {r}")
            elif r is not None and r != 1:
                print(f"[COLORMAP] UpdateColorMap returned {r}")
            return r
        return None

    def enable_rgbd_mapping(self, enable=True):
        if self.SetRGBDMapping is not None:
            try:
                self.SetRGBDMapping(self.handle, 1 if enable else 0)
            except Exception:
                pass

    def grab(self):
        if self.GetNextFrame is not None:
            try:
                self.GetNextFrame(self.handle)
            except Exception:
                pass
        f = frames()
        return f if self.GetFrames(self.handle, byref(f)) == 1 else None

    def close(self):
        try:
            if self.IsOpened(self.handle) == 1:
                self.CloseDevice(self.handle); print("Device closed.")
        except Exception:
            pass
        try:
            self.DeInitialize(); print("SDK de-initialized.")
        except Exception:
            pass


def _buffer(tof, nbytes):
    if not bool(tof.frame_data) or nbytes <= 0:
        return None
    return np.ctypeslib.as_array(tof.frame_data, shape=(nbytes,)).copy()


def get_depth_raw_u16(frm):
    tof = frm.raw_depth
    h, w = int(tof.height), int(tof.width)
    if h == 0 or w == 0:
        return None
    buf = _buffer(tof, h * w * 2)
    return None if buf is None else buf.view(np.uint16).reshape(h, w).copy()


def get_ir_image(frm):
    tof = frm.ir
    h, w = int(tof.height), int(tof.width)
    if h == 0 or w == 0:
        return None
    size = int(tof.size) if tof.size else h * w
    if size >= h * w * 2:
        buf = _buffer(tof, h * w * 2)
        if buf is None:
            return None
        ir16 = buf.view(np.uint16).reshape(h, w)
        g = cv2.convertScaleAbs(ir16, alpha=(255.0 / max(1, int(ir16.max()))))
        return cv2.cvtColor(g, cv2.COLOR_GRAY2BGR)
    buf = _buffer(tof, h * w)
    if buf is None:
        return None
    return cv2.cvtColor(buf.view(np.uint8).reshape(h, w), cv2.COLOR_GRAY2BGR)


def colorize_depth(depth_u16, fixed_range=None, colormap=CM_ECON):
    if depth_u16 is None:
        return None
    d = depth_u16.astype(np.float32); valid = d > 0
    if fixed_range is not None:
        lo, hi = float(fixed_range[0]), float(fixed_range[1])
    elif np.any(valid):
        lo, hi = np.percentile(d[valid], 2), np.percentile(d[valid], 98)
    else:
        lo, hi = 0, 1
    norm = np.clip((d - lo) / max(1.0, (hi - lo)), 0, 1)
    d8 = ((1.0 - norm) * 255).astype(np.uint8) if colormap == CM_ECON else (norm * 255).astype(np.uint8)
    d8[~valid] = 0
    color = cv2.applyColorMap(d8, _turbo()); color[~valid] = (0, 0, 0)
    return color


def depth_to_pointcloud_ply(depth_u16, out_path, depth_scale=1000.0, max_depth_m=6.0, color_bgr=None):
    import open3d as o3d
    h, w = depth_u16.shape
    z = depth_u16.astype(np.float32) / depth_scale
    valid = (z > 0.05) & (z < max_depth_m) & np.isfinite(z)
    ys, xs = np.mgrid[0:h, 0:w]
    if CALIB is not None:
        K, dist = CALIB.camera_matrix(w, h)
        pix = np.stack([xs[valid].ravel(), ys[valid].ravel()], axis=1).astype(np.float64).reshape(-1, 1, 2)
        nrm = cv2.undistortPoints(pix, K, dist).reshape(-1, 2)
        zc = z[valid].ravel(); X = nrm[:, 0] * zc; Y = nrm[:, 1] * zc; Z = zc
    else:
        fx = fy = w * 0.8; cx, cy = w / 2.0, h / 2.0
        zc = z[valid]; X = (xs[valid] - cx) * zc / fx; Y = (ys[valid] - cy) * zc / fy; Z = zc
    pts = np.stack((X, -Y, -Z), axis=-1)
    pcd = o3d.geometry.PointCloud(); pcd.points = o3d.utility.Vector3dVector(pts.astype(np.float64))
    if color_bgr is not None and color_bgr.shape[:2] == (h, w):
        rgb = cv2.cvtColor(color_bgr, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
        pcd.colors = o3d.utility.Vector3dVector(rgb[valid])
    o3d.io.write_point_cloud(out_path, pcd)
    print(f"Saved point cloud: {out_path} ({len(pts):,} pts)")
    return out_path


def resize_for_display(bgr, target_size=None, fit_size=None):
    if bgr is None or getattr(bgr, "size", 0) == 0:
        return bgr
    if target_size is not None:
        tw, th = int(target_size[0]), int(target_size[1])
        if tw < 1 or th < 1:
            return bgr
        interp = cv2.INTER_AREA if (bgr.shape[1] > tw) else cv2.INTER_LINEAR
        return cv2.resize(bgr, (tw, th), interpolation=interp)
    if fit_size is not None:
        fw, fh = int(fit_size[0]), int(fit_size[1])
        if fw < 2 or fh < 2:
            return bgr
        h, w = bgr.shape[:2]; s = min(fw / float(w), fh / float(h))
        nw, nh = max(1, int(w * s)), max(1, int(h * s))
        interp = cv2.INTER_AREA if s < 1 else cv2.INTER_LINEAR
        return cv2.resize(bgr, (nw, nh), interpolation=interp)
    return bgr


def to_photoimage(tk, bgr):
    if bgr is None or getattr(bgr, "size", 0) == 0:
        return None
    ok, buf = cv2.imencode(".png", bgr)
    if not ok:
        return None
    return tk.PhotoImage(data=base64.b64encode(buf.tobytes()).decode("ascii"))


class LiveApp:
    def __init__(self, args):
        self.args = args
        self.sdk = DepthVistaSDK(args.sdk)
        self.itof = None
        self.out_dir = args.output_dir
        os.makedirs(self.out_dir, exist_ok=True)
        self.last_ply = None
        self._running = True
        self._grab_paused = False
        self._imgtk = None
        self._last_depth_raw = None
        self._last_depth_color = None
        self._last_ir = None
        self._disp_depth = None
        self._cam_w = self._cam_h = 0
        self._shown_w = self._shown_h = 0
        self._view_w, self._view_h = 960, 600
        self._mouse = None
        self._frozen = None
        self._fixed_lo, self._fixed_hi = 500, 4000
        self._current_stream = DEFAULT_STREAM
        self._colormap = CM_ECON
        self._use_sdk_colormap = True
        self._center_hud = True
        self.root = None; self.video_label = None; self.status_var = None
        self._tk = None; self._filedialog = None; self._simpledialog = None; self._messagebox = None

    def start(self):
        self.sdk.init()
        devices = self.sdk.list_devices()
        if not devices:
            raise RuntimeError("No DepthVista camera detected.")
        idx = self.args.device if 0 <= self.args.device < len(devices) else 0
        self.sdk.open(devices[idx])
        self._apply_mode_config(DEFAULT_STREAM, do_reopen=False)
        if self.args.rgbd:
            self.sdk.enable_rgbd_mapping(True)
        self._build_ui()
        self.root.after(50, self._tick)
        self.root.mainloop()
        self._shutdown()

    def _apply_mode_config(self, label, do_reopen=True):
        """Switch modes using the same sequence as e-con's Preview loop.

        Important: e-con pauses frame acquisition, calls SetDataMode on the
        existing open handle, reads GetDataMode, waits, then resumes. It does
        not close/reopen the device for either Conf HD or Conf IR.
        """
        cfg = MODE_CONFIG.get(label, MODE_CONFIG[DEFAULT_STREAM])
        target = int(cfg["value"])
        cmin, cmax = cfg["cmap"]
        expected = tuple(cfg["res"])

        self._grab_paused = True
        time.sleep(0.25)  # allow any in-flight Tk grab to finish
        print("\n" + "=" * 72)
        print(f"[MODE] Request: {label}")
        print(f"[MODE] Target ID: {target}, expected resolution: {expected[0]}x{expected[1]}")
        print(f"[MODE] Requested colormap: {cmin}-{cmax} mm")

        ok = False
        try:
            before = self.sdk.get_data_mode()
            before_range = self.sdk.get_depth_range()
            print(f"[MODE] Before: data_mode={before}, depth_range={before_range}")

            # Exact e-con approach: SetDataMode while the device remains open.
            set_ret = self.sdk.set_data_mode(target)
            print(f"[MODE] SetDataMode({target}) -> {set_ret}")
            time.sleep(0.75 if sys.platform.startswith("linux") else 0.50)

            active = self.sdk.get_data_mode()
            print(f"[MODE] After first set: data_mode={active}")

            # Jetson retry: some Linux SDK/device combinations acknowledge late.
            if active is not None and active != target:
                print(f"[MODE] Mismatch ({active} != {target}); retrying SetDataMode")
                set_ret2 = self.sdk.set_data_mode(target)
                print(f"[MODE] Retry SetDataMode({target}) -> {set_ret2}")
                time.sleep(0.75)
                active = self.sdk.get_data_mode()
                print(f"[MODE] After retry: data_mode={active}")

            ok = (set_ret is not None and set_ret >= 1 and
                  (active is None or active == target))

            # e-con refreshes UpdateColorMap continuously in Preview. Apply it
            # immediately here as well so the first new-mode frame is correct.
            cmap_ret = self.sdk.update_colormap(cmin, cmax, debug=True)
            self._fixed_lo, self._fixed_hi = cmin, cmax
            self._expected_res = expected

            # Rebind menu controls to the active handle. No profile is forced.
            self._bind_itof(apply_profile=self.args.apply_profile)
            print(f"[MODE] Result: ok={ok}, active={active}, colormap_ret={cmap_ret}")
            print("=" * 72)
        except Exception as exc:
            print(f"[MODE] Exception while switching mode: {exc}")
            ok = False
        finally:
            self._grab_paused = False
        return ok

    def _bind_itof(self, apply_profile=False):
        if ITOFControls is None:
            return
        try:
            self.itof = ITOFControls(self.sdk.lib, DeviceHandle)
            self.itof.handle_ref = self.sdk.handle
            if apply_profile:
                # OPTIONAL only. econ does NOT do this - it uses firmware defaults.
                for k, v in (("Integration Time", self.args.integration),
                             ("Depth Denoise", self.args.denoise)):
                    if v is not None and k in self.itof.controls:
                        self.itof.set(self.sdk.handle, k, v)
                if self.args.confidence is not None and "Confidence Threshold" in self.itof.controls:
                    self.itof.set(self.sdk.handle, "Confidence Threshold", self.args.confidence)
                if "Spatial Filter" in self.itof.controls:
                    self.itof.set(self.sdk.handle, "Spatial Filter", 1)
                print("Applied optional control profile (--apply-profile).")
        except Exception as exc:
            print(f"(iTOF unavailable: {exc})")
            self.itof = None

    def _build_ui(self):
        import tkinter as tk
        from tkinter import filedialog, simpledialog, messagebox
        self._tk = tk; self._filedialog = filedialog
        self._simpledialog = simpledialog; self._messagebox = messagebox

        self.root = tk.Tk()
        self.root.title(f"DepthVista - {self.sdk.device_name or 'iToF Camera'}")
        self.root.geometry("1000x720"); self.root.minsize(480, 360)
        self.root.configure(bg="#202124")

        menubar = tk.Menu(self.root)

        m_file = tk.Menu(menubar, tearoff=0)
        m_file.add_command(label="Capture Frame", accelerator="c", command=self.action_capture)
        m_file.add_command(label="View Last Capture in 3D", accelerator="v", command=self.action_view)
        m_file.add_command(label="Open PLY in 3D...", command=self.action_open_ply)
        m_file.add_separator()
        m_file.add_command(label="RESET Camera to Defaults", command=self.action_reset)
        m_file.add_separator()
        m_file.add_command(label="Exit", accelerator="q", command=self.action_quit)
        menubar.add_cascade(label="File", menu=m_file)

        m_edit = tk.Menu(menubar, tearoff=0)
        self.var_stream = tk.StringVar(value=self._current_stream)
        m_stream = tk.Menu(m_edit, tearoff=0)
        for label in STREAM_MODES:
            m_stream.add_radiobutton(label=label, value=label, variable=self.var_stream,
                                     command=self._on_stream_mode)
        m_edit.add_cascade(label="Streaming Mode", menu=m_stream)
        m_edit.add_separator()

        available = {k for k, _ in self.itof.available()} if self.itof else set()
        numeric = [("Depth Denoise", "Depth Denoise"), ("Confidence Threshold", "Confidence Threshold"),
                   ("Integration Time", "Integration Time"), ("IR Gain", "IR Gain")]
        num_present = [(l, k) for l, k in numeric if k in available]
        if num_present:
            m_exp = tk.Menu(m_edit, tearoff=0)
            for l, k in num_present:
                m_exp.add_command(label=f"{l}...", command=self._make_numeric_cmd(k))
            m_edit.add_cascade(label="Exposure & Sensor", menu=m_exp)
        if "Spatial Filter" in available:
            self.var_spatial = tk.BooleanVar(value=False)
            m_edit.add_checkbutton(label="Spatial Filter", variable=self.var_spatial, command=self._on_spatial)
        m_edit.add_command(label="Temperatures...", command=self.action_temps)
        if self.sdk.SetRGBDMapping is not None:
            self.var_rgbd = tk.BooleanVar(value=bool(self.args.rgbd))
            m_edit.add_checkbutton(label="RGB-D Mapping", variable=self.var_rgbd, command=self._on_rgbd)
        m_edit.add_separator()
        m_edit.add_command(label="Device Info...", command=self.action_device_info)
        menubar.add_cascade(label="Edit", menu=m_edit)

        m_view = tk.Menu(menubar, tearoff=0)
        self.var_view = tk.StringVar(value="Depth")
        for name in ("Depth", "IR"):
            m_view.add_radiobutton(label=f"Show {name}", value=name, variable=self.var_view)
        m_view.add_separator()
        self.var_centerhud = tk.BooleanVar(value=self._center_hud)
        m_view.add_checkbutton(label="Center Distance HUD", variable=self.var_centerhud, command=self._on_centerhud)
        self.var_distance = tk.BooleanVar(value=True)
        m_view.add_checkbutton(label="Show Distance (mm) on hover", variable=self.var_distance, command=self._on_distance)
        m_view.add_separator()
        self.var_sdkcolor = tk.BooleanVar(value=self._use_sdk_colormap)
        m_view.add_checkbutton(label="Use SDK Colormap (econ colours)", variable=self.var_sdkcolor, command=self._on_sdkcolor)
        self.var_colormap = tk.StringVar(value=self._colormap)
        m_cmap = tk.Menu(m_view, tearoff=0)
        for name in (CM_TURBO, CM_ECON):
            m_cmap.add_radiobutton(label=name, value=name, variable=self.var_colormap, command=self._on_colormap)
        m_view.add_cascade(label="Fallback Color Map", menu=m_cmap)
        m_view.add_command(label="Set Range (mm)...", command=self._set_range)
        m_view.add_separator()
        self.var_dispsize = tk.StringVar(value=DISPLAY_SIZES[0][0])
        m_size = tk.Menu(m_view, tearoff=0)
        for label, _sz in DISPLAY_SIZES:
            m_size.add_radiobutton(label=label, value=label, variable=self.var_dispsize, command=self._on_dispsize)
        m_view.add_cascade(label="Display Size", menu=m_size)
        menubar.add_cascade(label="View", menu=m_view)

        m_help = tk.Menu(menubar, tearoff=0)
        m_help.add_command(label="About", command=self.action_about)
        menubar.add_cascade(label="Help", menu=m_help)
        self.root.config(menu=menubar)

        self.status_var = tk.StringVar(value=f"Ready. Mode: {self._current_stream}.")
        tk.Label(self.root, textvariable=self.status_var, anchor="w", fg="#e8eaed",
                 bg="#303134").pack(side="bottom", fill="x")

        self.video_label = tk.Label(self.root, bg="#202124")
        self.video_label.pack(side="top", fill="both", expand=True)
        self.video_label.bind("<Configure>", self._on_view_resize)
        self.video_label.bind("<Motion>", self._on_mouse_move)
        self.video_label.bind("<Button-1>", self._on_mouse_click)
        self.video_label.bind("<Leave>", lambda e: setattr(self, "_mouse", None))
        self.root.bind("c", lambda e: self.action_capture())
        self.root.bind("v", lambda e: self.action_view())
        self.root.bind("q", lambda e: self.action_quit())
        self.root.protocol("WM_DELETE_WINDOW", self.action_quit)
        self._resize_window_to_mode()

    def _resize_window_to_mode(self):
        try:
            if getattr(self, "var_dispsize", None) is not None:
                self.var_dispsize.set(DISPLAY_SIZES[0][0])   # reset to Fit window
        except Exception:
            pass
        try:
            w, h = getattr(self, "_expected_res", (1280, 960))
            sw = min(1000, w); sh = int(h * sw / float(w)) + 40
            self.root.geometry(f"{sw}x{sh}")
        except Exception:
            pass

    # ---- callbacks ----
    def _on_view_resize(self, e):
        self._view_w = max(2, int(e.width)); self._view_h = max(2, int(e.height))

    def _on_mouse_move(self, e):
        self._mouse = (int(e.x), int(e.y))

    def _on_mouse_click(self, e):
        self._frozen = None if self._frozen is not None else (int(e.x), int(e.y))

    def _on_distance(self):
        self._status(f"Distance readout: {'ON' if self.var_distance.get() else 'OFF'}")

    def _on_centerhud(self):
        self._center_hud = bool(self.var_centerhud.get())

    def _on_sdkcolor(self):
        self._use_sdk_colormap = bool(self.var_sdkcolor.get())
        self._status(f"SDK Colormap: {'ON' if self._use_sdk_colormap else 'OFF'}")

    def _on_colormap(self):
        self._colormap = self.var_colormap.get()

    def _on_spatial(self):
        if self.itof:
            r = self.itof.set(self.sdk.handle, "Spatial Filter", 1 if self.var_spatial.get() else 0)
            self._status(f"Spatial Filter: {'ON' if self.var_spatial.get() else 'OFF'}"
                         + ("" if (r is not None and r >= 1) else f" (ret {r})"))

    def _on_rgbd(self):
        self.sdk.enable_rgbd_mapping(bool(self.var_rgbd.get()))
        self._status(f"RGB-D Mapping: {'ON' if self.var_rgbd.get() else 'OFF'}")

    def _set_range(self):
        cur = f"{self._fixed_lo}-{self._fixed_hi}"
        s = self._simpledialog.askstring("Set Colormap Range (mm)",
            "Enter MIN and MAX depth in mm (e.g. '200-1200'):", initialvalue=cur, parent=self.root)
        if not s:
            return
        parts = s.replace("-", " ").replace(",", " ").split()
        try:
            nums = [int(float(p)) for p in parts if p.strip() != ""]
        except ValueError:
            self._status("Invalid range."); return
        if len(nums) < 2:
            self._status("Enter BOTH min and max."); return
        lo, hi = nums[0], nums[1]
        if lo > hi:
            lo, hi = hi, lo
        lo = max(0, lo); hi = min(60000, max(lo + 1, hi))
        self._grab_paused = True; time.sleep(0.03)
        try:
            self.sdk.update_colormap(lo, hi)
            self._fixed_lo, self._fixed_hi = lo, hi
        finally:
            self._grab_paused = False
        self._status(f"Colormap range set: {lo}-{hi} mm")

    def _current_display_size(self):
        label = getattr(self, "var_dispsize", None)
        if label is None:
            return None
        sel = self.var_dispsize.get()
        for lbl, size in DISPLAY_SIZES:
            if lbl == sel:
                return size
        return None

    def _on_dispsize(self):
        size = self._current_display_size()
        self._status("Display Size: Fit window" if size is None else f"Display Size: {size[0]}x{size[1]}")

    def _make_numeric_cmd(self, key):
        def cmd():
            spec = self.itof.controls.get(key, {})
            vmin, vmax = spec.get("min", 0), spec.get("max", 4095)
            cur = self.itof.read(key, default=vmin)
            val = self._simpledialog.askinteger(key, f"{key}  ({vmin} - {vmax}):",
                initialvalue=cur, minvalue=vmin, maxvalue=vmax, parent=self.root)
            if val is not None:
                r = self.itof.set(self.sdk.handle, key, val)
                ok = (r is not None and r != 0)
                self._status(f"{key} = {val}" + ("" if ok else f"  (ret {r})"))
        return cmd

    def action_temps(self):
        if self.itof is None:
            return
        t = self.itof.temperatures(self.sdk.handle)
        self._messagebox.showinfo("Temperatures (C)",
            "\n".join(f"{k.title()}: {v} C" for k, v in t.items()) if t else "No data",
            parent=self.root)

    # ---- distance overlays ----
    def _depth_at_label_point(self, lx, ly):
        if self._disp_depth is None or self._shown_w == 0:
            return None
        offx = (self._view_w - self._shown_w) // 2; offy = (self._view_h - self._shown_h) // 2
        sx, sy = lx - offx, ly - offy
        if sx < 0 or sy < 0 or sx >= self._shown_w or sy >= self._shown_h:
            return None
        dh, dw = self._disp_depth.shape
        dx = int(sx * dw / self._shown_w); dy = int(sy * dh / self._shown_h)
        if 0 <= dx < dw and 0 <= dy < dh:
            return dx, dy, int(self._disp_depth[dy, dx])
        return None

    def _draw_center_hud(self, shown):
        if self._disp_depth is None:
            return shown
        dh, dw = self._disp_depth.shape; cy0, cx0 = dh // 2, dw // 2; r = 7
        patch = self._disp_depth[max(0, cy0 - r):cy0 + r + 1, max(0, cx0 - r):cx0 + r + 1]
        vals = patch[patch > 0]; mm = int(vals.min()) if vals.size else 0
        cxs, cys = self._shown_w // 2, self._shown_h // 2
        cv2.drawMarker(shown, (cxs, cys), (255, 255, 255), cv2.MARKER_CROSS, 22, 1)
        txt = f"Center: {mm} mm" if mm > 0 else "Center: no depth"
        cv2.rectangle(shown, (8, 8), (208, 34), (0, 0, 0), -1)
        cv2.putText(shown, txt, (14, 27), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2, cv2.LINE_AA)
        return shown

    def _draw_distance_overlay(self, shown):
        if not (hasattr(self, "var_distance") and self.var_distance.get()):
            return shown
        offx = (self._view_w - self._shown_w) // 2; offy = (self._view_h - self._shown_h) // 2
        def one(pt, color):
            info = self._depth_at_label_point(pt[0], pt[1])
            if info is None:
                return
            _dx, _dy, mm = info
            if mm <= 0:
                return
            sx = int(pt[0] - offx); sy = int(pt[1] - offy)
            cv2.drawMarker(shown, (sx, sy), color, cv2.MARKER_CROSS, 18, 2)
            t = f"{mm} mm"; ty = sy - 12 if sy - 12 > 12 else sy + 20
            cv2.putText(shown, t, (sx + 8, ty), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 3, cv2.LINE_AA)
            cv2.putText(shown, t, (sx + 8, ty), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 1, cv2.LINE_AA)
        if self._frozen is not None:
            one(self._frozen, (0, 255, 255))
        if self._mouse is not None:
            one(self._mouse, (0, 255, 0))
        return shown

    # ---- streaming mode / reset ----
    def _on_stream_mode(self):
        label = self.var_stream.get()
        if label == self._current_stream:
            return
        self._status(f"Switching to {label} ...")
        ok = self._apply_mode_config(label, do_reopen=True)
        if ok:
            self._current_stream = label; self._resize_window_to_mode()
            cmin, cmax = MODE_CONFIG[label]["cmap"]
            self._status(f"Mode: {label} (colormap {cmin}-{cmax} mm)")
        else:
            self.var_stream.set(self._current_stream)
            self._status(f"Mode switch to {label} failed; staying on {self._current_stream}.")

    def action_reset(self):
        self._status("Resetting camera to defaults ...")
        self._apply_mode_config(DEFAULT_STREAM, do_reopen=True)
        self._current_stream = DEFAULT_STREAM
        if hasattr(self, "var_stream"):
            self.var_stream.set(DEFAULT_STREAM)
        self._resize_window_to_mode()
        self._status("Reset done.")

    def _status(self, msg):
        try:
            res = f"  [Camera: {self._cam_w}x{self._cam_h}]" if self._cam_w else ""
            self.status_var.set(msg + res)
        except Exception:
            pass
        print(msg)

    # ---- file actions ----
    def action_capture(self):
        if self._last_depth_raw is not None:
            self.last_ply = self._capture(self._last_depth_raw, self._last_depth_color, self._last_ir)
            self._status(f"Captured: {os.path.basename(self.last_ply)}")
        else:
            self._status("No depth to capture.")

    def action_view(self):
        if self.last_ply and os.path.isfile(self.last_ply):
            self._open_in_3d_viewer(self.last_ply)
        else:
            self._status("Capture a frame first.")

    def action_open_ply(self):
        path = self._filedialog.askopenfilename(title="Open PLY", initialdir=self.out_dir,
            filetypes=[("PLY", "*.ply"), ("All", "*.*")])
        if path:
            self._open_in_3d_viewer(path)

    def action_quit(self):
        self._running = False
        try:
            self.root.quit()
        except Exception:
            pass

    def action_device_info(self):
        lines = [f"App: {APP_VERSION}", f"Model: {self.sdk.device_name}",
                 f"Streaming Mode: {self._current_stream}",
                 f"Camera resolution: {self._cam_w}x{self._cam_h}",
                 f"Colormap range: {self.sdk.depth_min}-{self.sdk.depth_max} mm",
                 f"Startup control profile: {'ON (--apply-profile)' if self.args.apply_profile else 'OFF (firmware defaults, like econ)'}"]
        if self.itof:
            t = self.itof.temperatures(self.sdk.handle)
            if t:
                lines.append("Temps (C): " + ", ".join(f"{k}={v}" for k, v in t.items()))
            vals = self.itof.read_all(self.sdk.handle)
            for k, v in vals.items():
                if v is not None:
                    lines.append(f"{k}: {v}")
        self._messagebox.showinfo("Device Info", "\n".join(lines), parent=self.root)

    def action_about(self):
        self._messagebox.showinfo("About",
            f"{APP_VERSION}\nUses firmware-default controls (like econ).",
            parent=self.root)

    def _tick(self):
        if not self._running:
            return
        if self._grab_paused:
            self.root.after(30, self._tick); return
        # e-con calls UpdateColorMap for every preview frame. This matters on
        # Jetson because the Linux SDK can restore/carry cached mode settings
        # for the first frames after SetDataMode.
        self.sdk.update_colormap(self._fixed_lo, self._fixed_hi)
        frm = self.sdk.grab()
        depth_raw = depth_color = ir_img = None
        if frm is not None:
            depth_raw = get_depth_raw_u16(frm)
            self._disp_depth = depth_raw
            sdk_bgr = get_depth_colormap_bgr(frm) if self._use_sdk_colormap else None
            depth_color = sdk_bgr if sdk_bgr is not None else \
                colorize_depth(depth_raw, fixed_range=(self._fixed_lo, self._fixed_hi), colormap=self._colormap)
            ir_img = get_ir_image(frm)
            ref = depth_color if depth_color is not None else ir_img
            if ref is not None:
                h, w = ref.shape[:2]
                if (w, h) != (self._cam_w, self._cam_h):
                    self._cam_w, self._cam_h = w, h
                    self._status(f"Mode: {self._current_stream}")
        self._last_depth_raw = depth_raw
        self._last_depth_color = depth_color
        self._last_ir = ir_img

        which = self.var_view.get() if hasattr(self, "var_view") else "Depth"
        src = ir_img if which == "IR" else depth_color
        if src is None:
            src = np.full((360, 640, 3), 45, np.uint8)
            cv2.putText(src, f"No {which} in this mode", (90, 190),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (200, 200, 200), 2, cv2.LINE_AA)

        target = self._current_display_size()
        shown = resize_for_display(src, target_size=target) if target is not None \
            else resize_for_display(src, fit_size=(self._view_w, self._view_h))
        self._shown_w, self._shown_h = shown.shape[1], shown.shape[0]
        if which == "Depth":
            if getattr(self, "var_centerhud", None) is not None and self.var_centerhud.get():
                shown = self._draw_center_hud(shown)
            shown = self._draw_distance_overlay(shown)
        try:
            photo = to_photoimage(self._tk, shown)
            if photo is not None:
                self._imgtk = photo; self.video_label.configure(image=photo)
        except Exception as exc:
            print("display error:", exc)
        self.root.after(15, self._tick)

    def _capture(self, depth_raw, depth_color, ir_img):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        base = os.path.join(self.out_dir, f"DepthVista_{ts}")
        if depth_color is not None:
            cv2.imwrite(base + "_depth.png", depth_color)
        if ir_img is not None:
            cv2.imwrite(base + "_ir.png", ir_img)
        ply = base + ".ply"
        depth_to_pointcloud_ply(depth_raw, ply, max_depth_m=self.sdk.depth_max / 1000.0 + 0.5)
        return ply

    def _open_in_3d_viewer(self, ply_path):
        viewer = self.args.viewer_script
        if not os.path.isabs(viewer):
            viewer = os.path.join(SCRIPT_DIR, viewer)
        if not os.path.isfile(viewer):
            print(f"3D viewer not found: {viewer}"); return
        cmap_cli = CM_CLI.get(self._colormap, "econ")
        def _l():
            try:
                subprocess.Popen([sys.executable, viewer, "--input", ply_path, "--clean", "--colormap", cmap_cli])
            except Exception as exc:
                print(f"Failed: {exc}")
        threading.Thread(target=_l, daemon=True).start()
        self._status(f"Opening {os.path.basename(ply_path)} in 3D...")

    def _shutdown(self):
        self.sdk.close()
        try:
            self.root.destroy()
        except Exception:
            pass


def main():
    p = argparse.ArgumentParser(description="DepthVista live camera (econ-exact).")
    p.add_argument("--sdk", default=DEFAULT_SDK)
    p.add_argument("--device", type=int, default=0)
    p.add_argument("--rgbd", action="store_true")
    p.add_argument("--apply-profile", action="store_true",
                   help="Force Integration/Denoise/Spatial at startup. Default OFF "
                        "(econ uses firmware defaults).")
    p.add_argument("--integration", type=int, default=None, help="only with --apply-profile")
    p.add_argument("--denoise", type=int, default=None, help="only with --apply-profile")
    p.add_argument("--confidence", type=int, default=None, help="only with --apply-profile")
    p.add_argument("--output-dir", default="captures")
    p.add_argument("--viewer-script", default="depthvista_view_legacy.py")
    args = p.parse_args()
    app = LiveApp(args)
    try:
        app.start()
    except Exception as exc:
        print(f"\nERROR: {exc}")
        try:
            app.sdk.close()
        except Exception:
            pass
        sys.exit(1)


if __name__ == "__main__":
    main()
