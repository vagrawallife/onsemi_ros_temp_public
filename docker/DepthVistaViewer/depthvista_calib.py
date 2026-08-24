"""DepthVista depth calibration (econ factory intrinsics)."""
import os
import numpy as np
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
HD = {"fx":1.1786260199805336e+03,"fy":1.1779305316570319e+03,"cx":6.3047096467768142e+02,
      "cy":5.1062620776516582e+02,"dist":np.array([-4.1746822206320006e-01,2.4783588679674912e-01,
      -1.9068159241592949e-05,2.4839427295136239e-04,-1.1419837524194214e-01])}
VGA = {"fx":5.8931300999026678e+02,"fy":5.8896526582851595e+02,"cx":3.1523548233884071e+02,
       "cy":2.5531310388258291e+02,"dist":HD["dist"]}
_MAP={}
def _load():
    p=os.path.join(SCRIPT_DIR,"depth_intrinsic.yml")
    if not os.path.isfile(p): return
    try:
        import cv2
        fs=cv2.FileStorage(p,cv2.FILE_STORAGE_READ)
        def mat(n):
            nd=fs.getNode(n); return None if nd.empty() else nd.mat()
        for key,mn,dn in (("HD","SCCM_D","SCCD_D"),("VGA","SCCM_D_VGA","SCCD_D_VGA")):
            m,d=mat(mn),mat(dn); t=HD if key=="HD" else VGA
            if m is not None:
                t.update(fx=float(m[0,0]),fy=float(m[1,1]),cx=float(m[0,2]),cy=float(m[1,2]))
                if d is not None: t["dist"]=d.flatten().astype(np.float64)
        fs.release(); print("Loaded intrinsics from depth_intrinsic.yml")
    except Exception as e: print(f"(yml not parsed: {e})")
_load()
def intrinsics_for(w,h):
    b=HD if w>=1000 else VGA; cw=1280.0 if w>=1000 else 640.0; ch=960.0 if w>=1000 else 480.0
    sx,sy=w/cw,h/ch; return b["fx"]*sx,b["fy"]*sy,b["cx"]*sx,b["cy"]*sy,b["dist"]
def camera_matrix(w,h):
    fx,fy,cx,cy,dist=intrinsics_for(w,h)
    return np.array([[fx,0,cx],[0,fy,cy],[0,0,1]],dtype=np.float64),dist
def undistort_maps(w,h):
    k=(int(w),int(h))
    if k in _MAP: return _MAP[k]
    import cv2; K,dist=camera_matrix(w,h)
    m1,m2=cv2.initUndistortRectifyMap(K,dist,None,K,(int(w),int(h)),cv2.CV_16SC2)
    _MAP[k]=(m1,m2); return m1,m2
