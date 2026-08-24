"""
DepthVista 3D Viewer  (robust: uses Open3D's built-in high-level viewer)
=======================================================================

Earlier attempts with a custom SceneWidget GUI froze the mouse in some setups.
This version uses o3d.visualization.draw(), Open3D's own high-level viewer:
  - full, reliable mouse interaction (rotate / pan / zoom)
  - a built-in right-side SETTINGS panel (point size, lighting, materials,
    background, geometry list, etc.)
  - grey e-con-style background by default
It internally uses the new GUI but manages its own event loop, so it does not
suffer the freeze the hand-built SceneWidget did.

Pre-processing we keep:
  - near = blue, far = red (Turbo, colored by distance |z|)
  - --clean (statistical outlier removal), --flip (rescue old captures)
  - --voxel downsample, --point-size, --window WxH, --white

If your Open3D build lacks draw()/GUI (e.g. no Vulkan on Jetson), use
depthvista_view_legacy.py instead (OpenGL, no Vulkan).
"""
import argparse
import numpy as np
import open3d as o3d
import cv2

ECON_GREY = (0.90, 0.90, 0.92, 1.0)
WHITE_BG = (1.0, 1.0, 1.0, 1.0)


def turbo_by_distance(points):
    depth = np.abs(points[:, 2])           # capture stores z negative -> |z|=depth
    d_norm = (depth - depth.min()) / (depth.max() - depth.min() + 1e-6)
    d8 = (d_norm * 255).astype(np.uint8).reshape(-1, 1)
    cmap = getattr(cv2, "COLORMAP_TURBO", cv2.COLORMAP_JET)
    bgr = cv2.applyColorMap(d8, cmap).reshape(-1, 3)
    return bgr[:, ::-1].astype(np.float64) / 255.0   # BGR->RGB, 0..1


def load_and_prepare(args):
    print("Loading:", args.input)
    pcd = o3d.io.read_point_cloud(args.input)
    if len(pcd.points) == 0:
        raise SystemExit("No points found in PLY.")

    pts = np.asarray(pcd.points)
    print(f"Original points: {len(pts):,}")

    if args.flip:
        pts = pts.copy()
        pts[:, 2] *= -1.0
        pcd.points = o3d.utility.Vector3dVector(pts)
        print("Applied --flip (negated Z).")

    valid = np.isfinite(pts).all(axis=1)
    if not np.all(valid):
        pts = pts[valid]
        pcd.points = o3d.utility.Vector3dVector(pts)
        if pcd.has_colors():
            pcd.colors = o3d.utility.Vector3dVector(np.asarray(pcd.colors)[valid])

    if args.voxel and args.voxel > 0 and len(np.asarray(pcd.points)) > 300000:
        pcd = pcd.voxel_down_sample(voxel_size=args.voxel)
        print(f"Displayed points: {len(np.asarray(pcd.points)):,}")

    if args.clean:
        before = len(np.asarray(pcd.points))
        pcd, _ = pcd.remove_statistical_outlier(nb_neighbors=20, std_ratio=2.0)
        print(f"Cleanup: removed {before - len(np.asarray(pcd.points)):,} outliers")

    # Always give depth colors so it looks right even if the PLY had none.
    pcd.colors = o3d.utility.Vector3dVector(turbo_by_distance(np.asarray(pcd.points)))
    return pcd


def run_highlevel(pcd, args):
    """Open3D built-in viewer with the right-side Settings panel + reliable mouse."""
    bg = WHITE_BG if args.white else ECON_GREY
    try:
        win_w, win_h = (int(v) for v in args.window.lower().split("x"))
    except Exception:
        win_w, win_h = 1000, 640

    print("\nLaunching Open3D viewer (built-in Settings panel).")
    print("Mouse: Left=rotate, Right=pan, Wheel=zoom.  Panel is on the right.\n")

    o3d.visualization.draw(
        [{"name": "DepthVista", "geometry": pcd}],
        title="DepthVista 3D Viewer",
        width=win_w, height=win_h,
        bg_color=bg,
        point_size=int(args.point_size),
        show_ui=True,
    )


def run_legacy(pcd, args):
    """Fallback OpenGL viewer (no Vulkan). Mouse works; no side panel."""
    vis = o3d.visualization.Visualizer()
    vis.create_window(window_name="DepthVista 3D Viewer (OpenGL)",
                      width=1000, height=640)
    vis.add_geometry(pcd)
    opt = vis.get_render_option()
    opt.background_color = np.asarray((1.0, 1.0, 1.0) if args.white else ECON_GREY[:3])
    opt.point_size = float(args.point_size)
    print("\nFallback OpenGL viewer. Mouse: Left=rotate, Ctrl/Middle=pan, Wheel=zoom.\n")
    vis.run()
    vis.destroy_window()


def main():
    ap = argparse.ArgumentParser(description="DepthVista 3D viewer (built-in panel).")
    ap.add_argument("--input", required=True)
    ap.add_argument("--voxel", type=float, default=0.003)
    ap.add_argument("--point-size", type=float, default=3.0)
    ap.add_argument("--clean", action="store_true",
                    help="Remove flying-pixel streaks (statistical outliers).")
    ap.add_argument("--flip", action="store_true",
                    help="Negate Z to fix OLD captures where the face pointed away.")
    ap.add_argument("--white", action="store_true", help="White background.")
    ap.add_argument("--window", default="1000x640", help="Window size WxH.")
    ap.add_argument("--legacy", action="store_true",
                    help="Force the OpenGL fallback viewer (no panel, no Vulkan).")
    args = ap.parse_args()

    pcd = load_and_prepare(args)

    if args.legacy:
        return run_legacy(pcd, args)

    # Prefer the built-in panel viewer; fall back to OpenGL if unavailable.
    try:
        run_highlevel(pcd, args)
    except Exception as exc:
        print(f"High-level viewer unavailable ({exc}); using OpenGL fallback.")
        run_legacy(pcd, args)


if __name__ == "__main__":
    main()
