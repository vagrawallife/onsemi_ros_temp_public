"""DepthVista 3D viewer - legacy OpenGL (smooth Turbo). Keys: 1-5 bg, B cycle,
M colormap, +/- size, N colors, R reset, H help, Q quit."""
import argparse, numpy as np, open3d as o3d, cv2
BG=[("Light grey",(.9,.9,.92)),("White",(1,1,1)),("Dark grey",(.2,.2,.22)),("Black",(0,0,0)),("Light blue",(.94,.97,1))]
K2B={ord("1"):1,ord("2"):0,ord("3"):2,ord("4"):3,ord("5"):4}; CMAPS=["turbo","econ"]
def _turbo(): return getattr(cv2,"COLORMAP_TURBO",cv2.COLORMAP_JET)
def dcolors(P,cm):
    d=np.abs(P[:,2]); dn=(d-d.min())/(d.max()-d.min()+1e-6)
    d8=((1-dn)*255).astype(np.uint8).reshape(-1,1) if cm=="econ" else (dn*255).astype(np.uint8).reshape(-1,1)
    return cv2.applyColorMap(d8,_turbo()).reshape(-1,3)[:, ::-1].astype(np.float64)/255.0
def hp():
    print("""
============================================================
  DepthVista 3D Viewer - Controls
============================================================
  Background : 1 White  2 Light grey  3 Dark grey  4 Black  5 Light blue
               B = cycle backgrounds
  Colormap   : M = Turbo (near=Blue) <-> e-con (near=Orange)
  Point size : + increase   - decrease
  Colors     : N = depth colors <-> white
  View       : R = reset      Help: H      Quit: Q/Esc
  Mouse      : Left rotate,  Ctrl+Left/Middle pan,  Wheel zoom
============================================================
""")
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--input",required=True); ap.add_argument("--voxel",type=float,default=0.003)
    ap.add_argument("--point-size",type=float,default=3.0); ap.add_argument("--clean",action="store_true")
    ap.add_argument("--flip",action="store_true"); ap.add_argument("--colormap",choices=["turbo","econ"],default="econ")
    ap.add_argument("--bg",default="grey"); ap.add_argument("--width",type=int,default=1000); ap.add_argument("--height",type=int,default=640)
    a=ap.parse_args(); pcd=o3d.io.read_point_cloud(a.input)
    if len(pcd.points)==0: raise SystemExit("No points.")
    pts=np.asarray(pcd.points); print(f"Points:{len(pts):,}")
    if a.flip: pts=pts.copy(); pts[:,2]*=-1; pcd.points=o3d.utility.Vector3dVector(pts)
    vd=np.isfinite(pts).all(axis=1)
    if not np.all(vd):
        pts=pts[vd]; pcd.points=o3d.utility.Vector3dVector(pts)
        if pcd.has_colors(): pcd.colors=o3d.utility.Vector3dVector(np.asarray(pcd.colors)[vd])
    if a.voxel>0 and len(np.asarray(pcd.points))>300000: pcd=pcd.voxel_down_sample(voxel_size=a.voxel)
    if a.clean: pcd,_=pcd.remove_statistical_outlier(nb_neighbors=20,std_ratio=2.0)
    P=np.asarray(pcd.points); cm={"turbo":dcolors(P,"turbo"),"econ":dcolors(P,"econ")}; wh=np.ones((len(P),3))
    st={"bg":{"grey":0,"white":1,"dark":2,"black":3,"blue":4}[a.bg],"ps":float(a.point_size),"cm":a.colormap,"on":True}
    pcd.colors=o3d.utility.Vector3dVector(cm[st["cm"]])
    vis=o3d.visualization.VisualizerWithKeyCallback()
    vis.create_window(window_name="DepthVista 3D | press H for help",width=a.width,height=a.height)
    vis.add_geometry(pcd); o=vis.get_render_option(); o.background_color=np.asarray(BG[st["bg"]][1]); o.point_size=st["ps"]
    def bg(i):
        st["bg"]=i%len(BG); vis.get_render_option().background_color=np.asarray(BG[st["bg"]][1]); print("Background:",BG[st["bg"]][0]); return False
    for k,i in K2B.items(): vis.register_key_callback(k,(lambda ii:(lambda v:bg(ii)))(i))
    vis.register_key_callback(ord("B"),lambda v:bg(st["bg"]+1))
    def cyc(v):
        st["cm"]=CMAPS[(CMAPS.index(st["cm"])+1)%2]
        if st["on"]: pcd.colors=o3d.utility.Vector3dVector(cm[st["cm"]]); vis.update_geometry(pcd)
        print("Colormap:",st["cm"]); return False
    vis.register_key_callback(ord("M"),cyc)
    def inc(v): st["ps"]=min(20,st["ps"]+1); vis.get_render_option().point_size=st["ps"]; return False
    def dec(v): st["ps"]=max(1,st["ps"]-1); vis.get_render_option().point_size=st["ps"]; return False
    vis.register_key_callback(ord("="),inc); vis.register_key_callback(ord("+"),inc); vis.register_key_callback(ord("-"),dec)
    def tog(v):
        st["on"]=not st["on"]; pcd.colors=o3d.utility.Vector3dVector(cm[st["cm"]] if st["on"] else wh); vis.update_geometry(pcd); return False
    vis.register_key_callback(ord("N"),tog)
    vis.register_key_callback(ord("R"),lambda v:(vis.reset_view_point(True),False)[1])
    vis.register_key_callback(ord("H"),lambda v:(hp(),False)[1])
    hp(); vis.run(); vis.destroy_window()
if __name__=="__main__": main()
