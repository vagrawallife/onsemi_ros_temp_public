"""sdk_colormap.py - use the SDK's own depth_colormap + UpdateColorMap so colours
match econ exactly."""
import numpy as np
from ctypes import c_int
def bind_update_colormap(lib, device_handle_type):
    H=device_handle_type; fn4=None; fn3=None
    try:
        fn4=lib.UpdateColorMap; fn4.argtypes=[H,c_int,c_int,c_int]; fn4.restype=c_int
    except AttributeError: fn4=None
    if fn4 is None:
        try:
            fn3=lib.UpdateColorMap; fn3.argtypes=[H,c_int,c_int]; fn3.restype=c_int
        except AttributeError: fn3=None
    if fn4 is None and fn3 is None: return None
    def _u(handle,min_mm,max_mm,fmt=4):
        try:
            if fn4 is not None: return fn4(handle,int(min_mm),int(max_mm),int(fmt))
            return fn3(handle,int(min_mm),int(max_mm))
        except Exception as exc: print(f"(UpdateColorMap failed: {exc})"); return None
    return _u
def _arr(tof,ch,dtype):
    if not bool(tof.frame_data): return None
    h,w=int(tof.height),int(tof.width)
    if h==0 or w==0: return None
    n=h*w*ch*np.dtype(dtype).itemsize
    buf=np.ctypeslib.as_array(tof.frame_data,shape=(n,)).copy().view(dtype)
    return buf.reshape(h,w) if ch==1 else buf.reshape(h,w,ch)
def get_depth_colormap_bgr(frm):
    tof=getattr(frm,"depth_colormap",None)
    if tof is None: return None
    h,w=int(tof.height),int(tof.width)
    if h==0 or w==0 or not bool(tof.frame_data): return None
    size=int(tof.size) if tof.size else 0
    ch=3
    if size:
        per=size//(h*w)
        if per in (3,4): ch=per
        elif per==1: return None
    img=_arr(tof,ch,np.uint8)
    if img is None: return None
    if ch==4: img=img[:,:,:3]
    return np.ascontiguousarray(img)
def get_depth_raw_u16(frm):
    tof=getattr(frm,"raw_depth",None)
    return None if tof is None else _arr(tof,1,np.uint16)
