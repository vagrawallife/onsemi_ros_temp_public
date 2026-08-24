#!/usr/bin/env python3
"""
itof_publisher_node.py - ROS 2 publisher for the e-con DepthVista iToF camera
(See3CAM_TOF_CU13) for the onsemi_amr robot. Publishes depth colourmap, raw
depth (mm), IR, and camera_info for Foxglove / rviz2, alongside the CEM102 gas
sensor and camera publishers.

Runs with rclpy (system ROS Python; needs numpy + opencv, NOT Open3D).
Uses the DepthVista SDK exactly like our tested desktop app:
  * Conf HD data mode (1280x960), UpdateColorMap(min, max+1000, 4)
  * publishes the SDK's own depth_colormap (matches econ colours)
sensor_msgs built manually (no cv_bridge) to avoid NumPy-ABI issues.

Topics (namespace default /itof):
  depth/color        Image bgr8   (SDK colourised depth)
  depth/image_raw    Image 16UC1  (raw depth in mm)
    depth/points       PointCloud2  (XYZ points in metres, colored by distance)
  ir/image           Image mono8
  camera_info        CameraInfo
ROS params: sdk_path, device_index, mode, cmap_min, cmap_max, fps, frame_id, namespace
"""

import os
import time
import ctypes
from ctypes import (Structure, POINTER, byref,
                    c_char, c_int, c_int32, c_uint8, c_uint16, c_uint32, c_uint64)

import numpy as np

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
from sensor_msgs.msg import Image, CameraInfo, PointCloud2, PointField
from std_msgs.msg import Header


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SDK_LIB = "libDepthVistaSDK.so"

DATAMODE_CONF_IR = 1        # 640x480
DATAMODE_CONF_HD = 20       # 1280x960
MODES = {
    "conf_hd": dict(value=DATAMODE_CONF_HD, res=(1280, 960), cmap=(200, 4000)),
    "conf_ir": dict(value=DATAMODE_CONF_IR, res=(640, 480), cmap=(500, 6000)),
}


class DeviceHandle(Structure):
    _fields_ = [("serialNo", c_char * 50)]


class tofFrame(Structure):
    _fields_ = [("frame_data", POINTER(c_uint8)), ("width", c_uint16),
                ("height", c_uint16), ("pixel_format", c_uint8),
                ("size", c_uint32), ("time_stamp", c_uint64), ("frame_id", c_uint64)]


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


class DepthVistaSDK:
    def __init__(self, sdk_path):
        path = sdk_path if (sdk_path and os.path.isfile(sdk_path)) \
            else os.path.join(SCRIPT_DIR, SDK_LIB)
        lib_dir = os.path.dirname(os.path.abspath(path))
        os.environ["LD_LIBRARY_PATH"] = lib_dir + os.pathsep + os.environ.get("LD_LIBRARY_PATH", "")
        self.lib = ctypes.CDLL(path)
        self.handle = DeviceHandle()
        self._info = None
        self._bind()

    def _opt(self, name, argtypes):
        try:
            f = getattr(self.lib, name); f.argtypes = argtypes; f.restype = c_int
            return f
        except AttributeError:
            return None

    def _bind(self):
        L = self.lib
        self.Initialize = L.Initialize; self.Initialize.restype = c_int
        self.DeInitialize = L.DeInitialize; self.DeInitialize.restype = c_int
        self.GetDeviceCount = L.GetDeviceCount
        self.GetDeviceCount.argtypes = [POINTER(c_uint32)]; self.GetDeviceCount.restype = c_int
        self.GetDeviceInfo = L.GetDeviceInfo
        self.GetDeviceInfo.argtypes = [c_uint32, POINTER(DeviceInfo)]; self.GetDeviceInfo.restype = c_int
        self.OpenDevice = L.OpenDevice
        self.OpenDevice.argtypes = [DeviceInfo, POINTER(DeviceHandle)]; self.OpenDevice.restype = c_int
        self.IsOpened = L.IsOpened; self.IsOpened.argtypes = [DeviceHandle]; self.IsOpened.restype = c_int
        self.CloseDevice = L.CloseDevice; self.CloseDevice.argtypes = [DeviceHandle]; self.CloseDevice.restype = c_int
        self.SetDataMode = self._opt("SetDataMode", [DeviceHandle, c_int32])
        self.GetDataMode = self._opt("GetDataMode", [DeviceHandle, POINTER(c_int32)])
        self.UpdateColorMap = self._opt("UpdateColorMap", [DeviceHandle, c_int32, c_int32, c_int32])
        self.GetNextFrame = self._opt("GetNextFrame", [DeviceHandle])
        self.GetFrames = L.GetFrames
        self.GetFrames.argtypes = [DeviceHandle, POINTER(frames)]; self.GetFrames.restype = c_int

    def init_open(self, index):
        if self.Initialize() == 0:
            raise RuntimeError("SDK Initialize() failed")
        n = c_uint32(0)
        if self.GetDeviceCount(byref(n)) != 1 or n.value == 0:
            raise RuntimeError("No DepthVista device found")
        info = DeviceInfo()
        self.GetDeviceInfo(min(index, n.value - 1), byref(info))
        if self.OpenDevice(info, byref(self.handle)) < 1:
            raise RuntimeError("OpenDevice() failed")
        self._info = info
        return info.deviceName.decode(errors="ignore")

    def reopen(self):
        try:
            self.CloseDevice(self.handle)
        except Exception:
            pass
        time.sleep(0.3)
        h = DeviceHandle()
        if self.OpenDevice(self._info, byref(h)) >= 1:
            self.handle = h
            return True
        return False

    def set_mode(self, value, use_reopen):
        if use_reopen:
            self.reopen()
        elif self.SetDataMode:
            try:
                self.SetDataMode(self.handle, c_int32(value))
            except Exception:
                pass
            time.sleep(0.5)

    def update_colormap(self, dmin, dmax):
        if self.UpdateColorMap:
            try:
                self.UpdateColorMap(self.handle, int(dmin), int(dmax + 1000), 4)
            except Exception:
                pass

    def grab(self):
        if self.GetNextFrame:
            try:
                self.GetNextFrame(self.handle)
            except Exception:
                pass
        f = frames()
        return f if self.GetFrames(self.handle, byref(f)) == 1 else None

    def close(self):
        try:
            if self.IsOpened(self.handle) == 1:
                self.CloseDevice(self.handle)
        except Exception:
            pass
        try:
            self.DeInitialize()
        except Exception:
            pass


def _buf(tof, nbytes):
    if not bool(tof.frame_data) or nbytes <= 0:
        return None
    return np.ctypeslib.as_array(tof.frame_data, shape=(nbytes,)).copy()


def depth_colormap_bgr(frm):
    tof = frm.depth_colormap
    h, w = int(tof.height), int(tof.width)
    if h == 0 or w == 0 or not bool(tof.frame_data):
        return None
    per = (int(tof.size) // (h * w)) if tof.size else 3
    if per not in (3, 4):
        return None
    b = _buf(tof, h * w * per)
    if b is None:
        return None
    return np.ascontiguousarray(b.reshape(h, w, per)[:, :, :3])


def depth_raw_u16(frm):
    tof = frm.raw_depth
    h, w = int(tof.height), int(tof.width)
    if h == 0 or w == 0:
        return None
    b = _buf(tof, h * w * 2)
    return None if b is None else b.view(np.uint16).reshape(h, w)


def ir_mono8(frm):
    tof = frm.ir
    h, w = int(tof.height), int(tof.width)
    if h == 0 or w == 0 or not bool(tof.frame_data):
        return None
    b = _buf(tof, h * w * 2)
    if b is None:
        return None
    ir16 = b.view(np.uint16).reshape(h, w)
    mx = max(1, int(ir16.max()))
    return (ir16.astype(np.float32) * (255.0 / mx)).astype(np.uint8)


class ITOFPublisher(Node):
    def __init__(self):
        super().__init__("itof_publisher")
        self.declare_parameter("sdk_path", os.path.join(SCRIPT_DIR, SDK_LIB))
        self.declare_parameter("device_index", 0)
        self.declare_parameter("mode", "conf_hd")
        self.declare_parameter("cmap_min", 200)
        self.declare_parameter("cmap_max", 1500)
        self.declare_parameter("fps", 15.0)
        self.declare_parameter("frame_id", "itof_optical_frame")
        self.declare_parameter("namespace", "/itof")

        gp = lambda n: self.get_parameter(n).value
        self.frame_id = gp("frame_id")
        ns = str(gp("namespace")).rstrip("/")
        mode = gp("mode")
        mcfg = MODES.get(mode, MODES["conf_hd"])
        cmin, cmax = int(gp("cmap_min")), int(gp("cmap_max"))

        qos = QoSProfile(depth=5, reliability=ReliabilityPolicy.BEST_EFFORT,
                         history=HistoryPolicy.KEEP_LAST)
        self.pub_color = self.create_publisher(Image, f"{ns}/depth/color", qos)
        self.pub_depth = self.create_publisher(Image, f"{ns}/depth/image_raw", qos)
        self.pub_points = self.create_publisher(PointCloud2, f"{ns}/depth/points", qos)
        self.pub_ir = self.create_publisher(Image, f"{ns}/ir/image", qos)
        self.pub_info = self.create_publisher(CameraInfo, f"{ns}/camera_info", qos)

        self.sdk = DepthVistaSDK(gp("sdk_path"))
        name = self.sdk.init_open(int(gp("device_index")))
        self.get_logger().info(f"iToF opened: {name}")
        self.sdk.set_mode(mcfg["value"], use_reopen=(mcfg["value"] == DATAMODE_CONF_HD))
        self.sdk.update_colormap(cmin, cmax)

        self.timer = self.create_timer(1.0 / max(1.0, float(gp("fps"))), self._on_timer)
        self.get_logger().info(f"Publishing {ns}/* (mode={mode}, cmap={cmin}-{cmax} mm).")

    def _hdr(self):
        h = Header(); h.stamp = self.get_clock().now().to_msg(); h.frame_id = self.frame_id
        return h

    def _img(self, arr, encoding):
        m = Image(); m.header = self._hdr()
        m.height, m.width = int(arr.shape[0]), int(arr.shape[1])
        m.encoding = encoding; m.is_bigendian = 0
        ch = 1 if arr.ndim == 2 else arr.shape[2]
        m.step = m.width * ch * arr.dtype.itemsize
        m.data = np.ascontiguousarray(arr).tobytes()
        return m

    def _camera_info(self, w, h):
        ci = CameraInfo(); ci.header = self._hdr(); ci.width = int(w); ci.height = int(h)
        if w >= 1000:
            fx, fy, cx, cy = 1178.626, 1177.931, 630.471, 510.626
        else:
            fx, fy, cx, cy = 589.313, 588.965, 315.235, 255.313
        ci.distortion_model = "plumb_bob"
        ci.d = [-0.41747, 0.24784, -1.907e-05, 2.484e-04, -0.11420]
        ci.k = [fx, 0, cx, 0, fy, cy, 0, 0, 1.0]
        ci.r = [1.0, 0, 0, 0, 1.0, 0, 0, 0, 1.0]
        ci.p = [fx, 0, cx, 0, 0, fy, cy, 0, 0, 0, 1.0, 0]
        return ci

    def _point_cloud(self, depth, color_bgr):
        height, width = depth.shape
        if width >= 1000:
            fx, fy, cx, cy = 1178.626, 1177.931, 630.471, 510.626
        else:
            fx, fy, cx, cy = 589.313, 588.965, 315.235, 255.313

        u, v = np.meshgrid(np.arange(width), np.arange(height))
        z = depth.astype(np.float32) * 0.001
        valid = z > 0.0
        x = (u.astype(np.float32) - cx) * z / fx
        y = (v.astype(np.float32) - cy) * z / fy
        xyz = np.stack((x, y, z), axis=-1)
        xyz[~valid] = np.nan

        rgb = np.zeros((height, width), dtype=np.uint32)
        if color_bgr is not None and color_bgr.shape[:2] == (height, width):
            blue = color_bgr[:, :, 0].astype(np.uint32)
            green = color_bgr[:, :, 1].astype(np.uint32)
            red = color_bgr[:, :, 2].astype(np.uint32)
            rgb = (red << 16) | (green << 8) | blue
        rgb[~valid] = 0

        points = np.empty((height, width), dtype=[
            ('x', '<f4'), ('y', '<f4'), ('z', '<f4'), ('rgb', '<f4')])
        points['x'] = xyz[:, :, 0]
        points['y'] = xyz[:, :, 1]
        points['z'] = xyz[:, :, 2]
        points['rgb'] = rgb.view('<f4')

        msg = PointCloud2()
        msg.header = self._hdr()
        msg.height = height
        msg.width = width
        msg.fields = [
            PointField(name='x', offset=0, datatype=PointField.FLOAT32, count=1),
            PointField(name='y', offset=4, datatype=PointField.FLOAT32, count=1),
            PointField(name='z', offset=8, datatype=PointField.FLOAT32, count=1),
            PointField(name='rgb', offset=12, datatype=PointField.FLOAT32, count=1),
        ]
        msg.is_bigendian = False
        msg.point_step = 16
        msg.row_step = msg.point_step * width
        msg.is_dense = bool(np.all(valid))
        msg.data = points.tobytes()
        return msg

    def _on_timer(self):
        frm = self.sdk.grab()
        if frm is None:
            return
        col = depth_colormap_bgr(frm)
        if col is not None:
            self.pub_color.publish(self._img(col, "bgr8"))
            self.pub_info.publish(self._camera_info(col.shape[1], col.shape[0]))
        draw = depth_raw_u16(frm)
        if draw is not None:
            #self.pub_depth.publish(self._img(draw, "16UC1"))
            self.pub_points.publish(self._point_cloud(draw, col))
        #ir = ir_mono8(frm)
        #if ir is not None:
        #    self.pub_ir.publish(self._img(ir, "mono8"))

    def destroy_node(self):
        try:
            self.sdk.close()
        except Exception:
            pass
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = ITOFPublisher()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
