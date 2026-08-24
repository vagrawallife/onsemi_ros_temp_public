"""itof_controls.py - EXACT econ console controls for See3CAM_TOF_CU13.
Depth Denoise 0-15, Confidence Threshold 0-4095, Integration Time 0-850,
IR Gain 0-100, Spatial Filter 0/1 (c_int setter), Temperatures (read)."""
from ctypes import POINTER, byref, c_int, c_uint16, c_uint32, c_float
class ITOFControls:
    _SPEC=[("Depth Denoise","SetDepthNoise","GetDepthNoise",c_uint32,c_uint32,0,15),
           ("Confidence Threshold","SetConfidenceThreshold","GetConfidenceThreshold",c_uint16,c_uint16,0,4095),
           ("Integration Time","SetIntegrationTime","GetIntegrationTime",c_uint16,c_uint16,0,850),
           ("IR Gain","SetTOFIRGain","GetTOFIRGain",c_uint16,c_uint16,0,100),
           ("Spatial Filter","SetDepthSpatialFilter",None,c_uint16,c_int,0,1)]
    def __init__(self,lib,H):
        self.lib=lib; self.H=H; self.controls={}; self.handle_ref=None; self._bind()
    def _fn(self,name,argtypes,restype=c_int):
        try:
            f=getattr(self.lib,name); f.argtypes=argtypes; f.restype=restype; return f
        except AttributeError: return None
    def _bind(self):
        for label,sn,gn,ct,sct,vmin,vmax in self._SPEC:
            setter=self._fn(sn,[self.H,sct]); getter=self._fn(gn,[self.H,POINTER(ct)]) if gn else None
            if setter is not None:
                self.controls[label]={"set":setter,"get":getter,"ctype":ct,"set_ctype":sct,
                                      "min":vmin,"max":vmax,"toggle":(label=="Spatial Filter")}
        self.get_laser_temp=self._fn("GetLaserBoardTemperatureData",[self.H,POINTER(c_float)])
        self.get_base_temp=self._fn("GetBaseBoardTemperatureData",[self.H,POINTER(c_float)])
        self.get_sensor_temp=self._fn("GetSensorDieTemperatureData",[self.H,POINTER(c_float)])
    def available(self):
        order=["Depth Denoise","Confidence Threshold","Integration Time","IR Gain","Spatial Filter"]
        return [(k,self.controls[k]) for k in order if k in self.controls]
    def read(self,label,default=None):
        s=self.controls.get(label)
        if not s or s["get"] is None or self.handle_ref is None: return default
        v=s["ctype"]()
        try:
            if s["get"](self.handle_ref,byref(v))>=1: return int(v.value)
        except Exception: pass
        return default
    def set(self,handle,label,value):
        s=self.controls.get(label)
        if not s: return None
        try: return s["set"](handle,s["set_ctype"](int(value)))
        except Exception as exc: print(f"(set {label}={value} failed: {exc})"); return None
    def read_all(self,handle):
        self.handle_ref=handle
        return {k:self.read(k) for k,_ in self.available() if self.controls[k]["get"]}
    def temperatures(self,handle):
        out={}
        for key,fn in (("laser",self.get_laser_temp),("base",self.get_base_temp),("sensor",self.get_sensor_temp)):
            if fn is None: continue
            v=c_float()
            try:
                if fn(handle,byref(v))>=1: out[key]=round(v.value,1)
            except Exception: pass
        return out
    def apply_startup_profile(self,handle,integration=None,denoise=None,confidence=None,spatial=True):
        applied={}
        if integration is not None and "Integration Time" in self.controls:
            if self.set(handle,"Integration Time",integration) not in (0,None): applied["Integration Time"]=integration
        if denoise is not None and "Depth Denoise" in self.controls:
            if self.set(handle,"Depth Denoise",denoise) not in (0,None): applied["Depth Denoise"]=denoise
        if confidence is not None and "Confidence Threshold" in self.controls:
            if self.set(handle,"Confidence Threshold",confidence) not in (0,None): applied["Confidence Threshold"]=confidence
        if spatial and "Spatial Filter" in self.controls:
            r=self.set(handle,"Spatial Filter",1)
            if r is not None and r>=1: applied["Spatial Filter"]="ON"
        return applied
    def apply_clean_profile(self,handle,integration=500,confidence=None,denoise=8):
        return self.apply_startup_profile(handle,integration=integration,denoise=denoise,confidence=confidence,spatial=True)
