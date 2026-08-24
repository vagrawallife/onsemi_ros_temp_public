# DepthVista iToF Camera Application

Live viewer and capture tool for the **e-con Systems DepthVista iToF camera**
(See3CAM_TOF_CU13), integrated into the `onsemi_amazing_hand` ROS Jazzy
container for NVIDIA Jetson AGX.

It streams the depth video, captures a frame (depth/IR/RGB PNG + a `.ply` point
cloud), and opens the capture in an interactive 3D viewer.

---

## Requirements

- NVIDIA Jetson AGX (aarch64) with the ROS Jazzy container image
- e-con **See3CAM_TOF_CU13** iToF camera (USB)
- A display attached to the Jetson (the viewer is a GUI app)
- e-con **DepthVista ARM64 SDK** — `libDepthVistaSDK.so` and its dependent
  `.so` files, placed inside `DepthVistaViewer/`

---

## Layout

Place the app folder next to the Dockerfile:

```
onsemi_amazing_hand/
└── docker/
    └── DepthVistaViewer/
        ├── depthvista_camera_live.py
        ├── depthvista_view_legacy.py
        ├── depthvista_open3d_gui_viewer_full.py
        ├── itof_controls.py
        └── libDepthVistaSDK.so      (+ dependent .so files)
```

---

## Build the image

```bash
cd onsemi_amazing_hand/docker
docker build -t amazing_hand:jazzy .
```

> Do I need to rebuild after changing the Python files?
> - If the files are **COPY-ed into the image** (default): **yes**, rebuild so the
>   new files are baked in.
> - If you **bind-mount** the folder at run time
>   (`-v .../DepthVistaViewer:/opt/depthvista`): **no** rebuild — just restart the
>   container. Handy while developing.

---

## Run the container

```bash
xhost +local:root

docker run -it --rm \
    --runtime nvidia \
    --network host \
    --privileged \
    -e NVIDIA_DRIVER_CAPABILITIES=graphics,compute,utility,display \
    -e NVIDIA_VISIBLE_DEVICES=all \
    -e DISPLAY="${DISPLAY:-:0}" \
    -v /tmp/.X11-unix:/tmp/.X11-unix \
    -v /dev:/dev \
    -v /run/udev:/run/udev:ro \
    amazing_hand:jazzy \
    bash
```

---

## Run the application (inside the container)

Check the camera is detected:

```bash
ls /dev/video*
v4l2-ctl --list-devices        # should list See3CAM_TOF_CU13
```

Start the live camera:

```bash
depthvista
```

Captures are saved to `/opt/depthvista/captures/`.

---

## How to operate the app

The window has a menu bar (**File / Edit / View / Help**) and the live video.

**File**
- **Capture Frame** (key `c`) — saves depth/IR/RGB PNG + a `.ply`
- **View Last Capture in 3D** (key `v`) — opens the last capture in the 3D viewer
- **Open PLY in 3D…** — pick any saved `.ply` to view
- **Exit** (key `q`)

**Edit** (camera settings; only options this camera supports are shown)
- **Exposure & Sensor** — Integration Time, IR Gain, Confidence Threshold,
  Depth Denoise (values open a dialog with the valid range)
- **Post-Processing Filters** — Spatial, Temporal, Flying Pixel, Planarization,
  Undistort, Confidence Mode (checkboxes)
- **RGB-D Mapping** — toggle
- **Device Info…** — model, temperatures, current settings
- *(Data Mode / Depth Range appear only on cameras that support them; the CU13
  does not, so they are hidden.)*

**View**
- **Show Depth / IR / RGB** — choose which stream fills the window
- **Depth Color Scale** — Auto (per-frame) or Fixed (absolute mm)
- **Set Fixed Range (mm)…** — set the min/max for the Fixed scale
- **Display Size** — match the on-screen view to the RGB camera resolution

### Depth colors
Turbo colormap: **near = blue, far = red**, black = no return.

### Close-up subjects (CU13 has a fixed range)
The CU13 has no Near/Far switch. If a subject ~0.5 m away shows up **black**,
raise **Edit ▸ Exposure & Sensor ▸ Integration Time** (160 = black face,
500 = clear). The app already applies 500 as a startup default.
Verified limits: Integration Time **0–800**, IR Gain **0–4**,
Depth Denoise **0–4**, Confidence Threshold **0–4095**.
Depth becomes valid after a brief (~1 s) warm-up.

---

## 3D viewer — keyboard shortcuts

The 3D viewer (opened by `v` or `depthvista-view`) is a smooth OpenGL window.

```
Background : 1 = White   2 = Light grey   3 = Dark grey   4 = Black   5 = Light blue
             B = cycle backgrounds
Point size : + / -
Colors     : N = toggle Turbo depth colors  /  white points
View       : R = reset view
Help       : H = print this list to the console
Quit       : Q or Esc

Mouse      : Left = rotate,  Ctrl+Left or Middle = pan,  Wheel = zoom
```

Open a saved capture directly:

```bash
depthvista-view --input captures/DepthVista_XXXX.ply --clean
```

---

## Keeping captures on the host

Bind-mount a host folder into the captures path:

```bash
docker run ... -v $HOME/depthvista_captures:/opt/depthvista/captures ...
```

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `cannot open shared object libDepthVistaSDK.so` | Use the **aarch64** SDK build (not the Windows DLL); place it in `DepthVistaViewer/`. |
| `No DepthVista camera detected` | Run with `--privileged -v /dev:/dev`; re-plug the camera; verify `ls /dev/video*`. |
| Face black at ~0.5 m | Raise **Edit ▸ Exposure & Sensor ▸ Integration Time** (~500). |
| Near/Far or Data Mode does nothing | Expected on CU13 — not supported (those menus are hidden). |
| 3D viewer `Unable to create Vulkan instance` | The default 3D viewer is OpenGL (no Vulkan) — use it (`depthvista_view_legacy.py`). |
| `cannot connect to display` | Run `xhost +local:root`; pass `-e DISPLAY` + the X11 mount. |
| Depth looks black for ~1 s | Normal iToF warm-up; depth becomes valid after ~20 frames. |
