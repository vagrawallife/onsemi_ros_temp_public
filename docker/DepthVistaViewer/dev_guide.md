# DepthVista — Developer Guide & Learnings

Internal engineering notes for the DepthVista iToF application: how it works, why
key decisions were made, every problem we hit and its fix, and how to reproduce
the whole project from scratch. Keep this with the source.

Camera: e-con **See3CAM_TOF_CU13** (iToF).
Targets: Windows (dev) and NVIDIA **Jetson AGX** (ROS Jazzy, Py3.12 container).
Upstream: `econsystems/DepthVista` (Qt C++ viewer) and
`econsystems/depthVistaCmd` (the authoritative **Python bindings**:
`input.py`, `main.py`, `iTOF_Controls.py`).

---

## 1. Architecture

```
depthvista_camera_live.py   Live app: open camera, stream, capture PNG + .ply,
                            launch 3D viewer. ctypes bindings to the SDK.
itof_controls.py            CU13 on-camera post-processing (denoise / spatial /
                            flying-pixel / confidence) via econ iTOF_Controls API.
depthvista_open3d_gui_viewer_full.py
                            Open3D *new GUI* viewer (side panel). Uses Filament
                            -> Vulkan. Great on desktop; needs Vulkan on Jetson.
depthvista_view_legacy.py   Open3D *legacy* viewer (OpenGL, no Vulkan). Jetson
                            fallback when Vulkan is unavailable.
depthvista_camera_test.py   AR0234 / webcam test harness (synthetic depth) so the
                            pipeline can be developed without the iToF camera.
diag_probe.py / diag_probe2.py
                            SDK bring-up + warm-up diagnostics.
```

Data flow: `GetFrames()` -> `raw_depth` (uint16 mm) -> colorize (Turbo) for the
live window; on capture, back-project depth to a `.ply` and (optionally) open it
in a 3D viewer.

---

## 2. The SDK ctypes bindings (the crash story)

**Symptom:** on CU13, every handle call crashed with
`access violation reading 0xFFFFFFFFFFFFFFFF`, even trivial `SetDataMode`.

**Root cause:** our hand-written ctypes structs didn't match the SDK. The killer
was `DeviceHandle`. econ's `input.py` defines it as a **50-byte struct**, but we
had an 8-byte pointer. `OpenDevice` wrote 50 bytes into 8 -> memory corruption ->
every later handle call dereferenced garbage.

**The rules that MUST hold (match econ `input.py` + `main.py` exactly):**

- `DeviceHandle` = `c_char * 50`  (NOT `c_void_p`).
- `DeviceInfo` ends with a nested **`GMSLDeviceInfo`** (`gmsldevinfo`).
- `frames` has **14** `tofFrame` members; depth is in **`raw_depth`** (uint16 mm).
- `tofFrame` order: `frame_data, width, height, pixel_format(u8), size(u32),
  time_stamp(u64), frame_id(u64)`.
- `DeviceHandle` is passed **by value** to handle-based calls.
- `DataMode.Depth_IR = 0` (not 2). `Depth = 2`, `IR = 3`.

**Takeaway:** never hand-guess vendor structs. Pull them from the vendor's own
Python sample and mirror field order/types precisely.

---

## 3. Depth specifics

- **Warm-up:** iToF returns zeros for ~20 frames after open; depth then becomes
  valid. Don't grab a single frame right after open and assume it has data.
- **`-29` returns:** `SetDataMode` / `SetDepthRange` may return `-29` on CU13.
  This is **non-fatal** — the camera streams in its default depth+IR mode.
- **Colorize ourselves:** we Turbo-colormap `raw_depth` with **percentile
  auto-scaling** (2–98%). This is robust across depth ranges and doesn't depend
  on the SDK colormap buffer.
- **Holes are physical:** black regions in the depth map are pixels with no IR
  return (dark/absorbing/too-far surfaces). Confirmed by the IR image. Those
  pixels are simply absent from the point cloud — not a bug.

---

## 4. Point-cloud orientation (the "face on the far side" fix)

We first flipped only Y -> `(x, -y, z)`. That is a **mirror** (determinant -1),
which puts the face on the *back* of the cloud (you had to rotate 180° to see the
nose). The correct camera->world mapping negates **both Y and Z**:

```
pts = (x, -y, -z)      # proper 180° rotation about X, determinant +1
```

This keeps the scene **upright** AND puts the **face toward the viewer**.

- New captures use `(x,-y,-z)` and need no flip.
- OLD captures (saved as `(x,-y,z)`) can be rescued in the viewer with **`--flip`**
  (which negates Z at load time).

Intrinsics are still the placeholder `fx = fy = w*0.8`, `cx,cy = center`. For
metric-accurate geometry, read true intrinsics via `CalibReadDepthIntrinsic`
(documented in the SDK API PDF) — future work.

---

## 5. On-camera cleanup (CU13)

`iTOF_Controls.py` (econ) exposes post-processing that runs ON the camera:
`SetDepthNoise` (denoise), `SetDepthSpatialFilter`, flying-pixel filter,
`SetConfidenceThreshold`, `SetIntegrationTime`, `SetTOFIRGain`. Enabling these
removes the diagonal "flying-pixel" streaks at the source — better than post-hoc
outlier removal. We wrap them in `itof_controls.py` and apply a sensible profile
at startup. Flags: `--no-filters`, `--confidence N`.

The viewer's `--clean` (statistical outlier removal) is a second, optional pass.

---

## 6. GUI decisions

- **Live window:** OpenCV (`imshow`) with an on-screen toolbar (Capture / View 3D
  / Quit) drawn on the frame + a mouse callback. Keys `c/v/q` work only when the
  window is focused; closing the window (X) quits (checked via
  `cv2.getWindowProperty(..., WND_PROP_VISIBLE)`). No stdin is read.
- **Do NOT mix PyQt + Open3D in threads** — it crashes with
  `QApplication was not created in the main() thread`. Use Open3D's own GUI.
- **Viewer opened in a daemon thread** so the live stream keeps running.
- **Smoothness:** big clouds (~800k pts) stutter. The live app opens the viewer
  with `--clean` (default voxel 0.003 -> ~150–200k pts) for smooth rotation like
  the e-con web viewer. Use `--voxel 0` for full resolution.
- **Background:** e-con-style light grey `(0.90, 0.90, 0.92)`, with buttons to
  switch Grey / Light Blue / White.

---

## 7. Cross-platform / dependency landmines

- **numpy < 2 is mandatory.** open3d/opencv wheels (and mediapipe) are built
  against NumPy 1.x; NumPy 2 causes
  `A module compiled using NumPy 1.x cannot be run in NumPy 2.x`. Keep `numpy<2`.
- **No matplotlib.** We removed it; the Turbo colormap is done with OpenCV
  (`cv2.applyColorMap` + BGR→RGB). One less NumPy-2-sensitive dependency.
- **SDK is platform-specific.** Windows uses `DepthVistaSDK.dll`; Jetson needs
  the **aarch64 `libDepthVistaSDK.so`** (+ deps). The app auto-selects by OS and
  loads the library from its own folder, registering that folder so dependent
  libraries resolve (`os.add_dll_directory` on Windows; `LD_LIBRARY_PATH` on
  Linux).

---

## 8. Windows notes

- Put `DepthVistaSDK.dll` **and its dependent DLLs** next to the scripts; the app
  loads it automatically. The "or one of its dependencies" error means a sibling
  DLL is missing from the folder / search path (we fixed this by adding the
  folder via `os.add_dll_directory`).
- Confirm 64-bit Python vs 64-bit SDK (bitness mismatch also fails to load).

---

## 9. Jetson AGX / Docker notes

- **Reuse the container's `/opt` venv** (it already has opencv + numpy<2). Only
  **add open3d**; do not create a second venv or reinstall numpy/opencv.
- **Open3D on aarch64:** official open3d has **no ARM64 Linux wheel** (isl-org
  v0.19 notes: "ARM64 Linux builds are not available"). Install
  **`open3d-unofficial-arm`** — it ships ARM64 Py3.10–3.13 wheels and imports as
  plain `open3d` (no code change). On x86/Win/mac it transparently installs
  official open3d, so one Dockerfile works everywhere.
- **Vulkan:** the *new* Open3D GUI renders via Filament→Vulkan. Containers often
  lack Vulkan (`vulkaninfo: command not found`, or `Unable to create Vulkan
  instance Result=-9`). Options:
  1. Install `libvulkan1 vulkan-tools` and run with
     `-e NVIDIA_DRIVER_CAPABILITIES=graphics,compute,utility,display`
     `--runtime nvidia`. On Tegra you may also need to bind-mount the host ICD:
     `-v /usr/share/vulkan/icd.d:/usr/share/vulkan/icd.d:ro` and
     `-v /usr/lib/aarch64-linux-gnu/tegra:/usr/lib/aarch64-linux-gnu/tegra:ro`.
  2. Or just use **`depthvista_view_legacy.py`** (OpenGL, no Vulkan). Recommended
     on Jetson for reliability.
- **USB + display:** `--privileged -v /dev:/dev -v /run/udev:/run/udev:ro` for the
  camera; `-e DISPLAY` + `-v /tmp/.X11-unix:/tmp/.X11-unix` (and
  `xhost +local:root`) for the GUI.
- **Build context:** `COPY` can only read inside the context. Keep
  `PythonExample/DepthVistaViewer/` **inside `docker/`** so you can build from
  `docker/` with the default command (no `-f`). `COPY` path becomes
  `PythonExample/DepthVistaViewer/`. If the app lived outside `docker/`, you'd
  have to build from the repo root with `-f docker/Dockerfile .`.

---

## 10. Dockerfile optimization (what we changed)

Applied to the amazing_hand Dockerfile without changing behavior:

- **`ENV KEY = value` (spaces) -> `ENV KEY=value`.** The space form bakes the
  spaces into the variable, so the `NVIDIA_*` GPU vars were malformed.
- **~50 `apt-get` lines -> one grouped install** with `--no-install-recommends`
  and a single `apt-get clean && rm -rf /var/lib/apt/lists/*` (smaller image).
- **Rust/uv installed once** (was ~4×/3×); removed **no-op curl lines**
  (`curl ... https://sh.rustup.rs` with no `| sh`; `curl -y ...` — curl has no
  `-y`).
- **Order deps before `COPY` the app** so editing app code only rebuilds the
  small final layer.
- Added `DEBIAN_FRONTEND=noninteractive`.

---

## 11. Reproduce from scratch (checklist)

1. Clone `econsystems/depthVistaCmd`; copy the ctypes structs from
   `Source/Windows/Python/DepthVistaCmd/input.py` + `main.py` **verbatim**
   (esp. `DeviceHandle=c_char*50`, `DeviceInfo`+`GMSLDeviceInfo`, 14-member
   `frames`, `DataMode.Depth_IR=0`).
2. Implement `grab()` = best-effort `GetNextFrame` then `GetFrames`.
3. Colorize `raw_depth` (Turbo, percentile). Warm up ~20 frames.
4. Back-project to `.ply` with `(x,-y,-z)`.
5. Add on-camera filters from `iTOF_Controls.py`.
6. Viewer: Open3D new GUI (desktop) + legacy OpenGL (Jetson); grey bg; `--clean`,
   `--flip`, `--voxel`.
7. Pin `numpy<2`; use OpenCV colormap (no matplotlib).
8. Package: SDK library next to scripts; auto-load + register folder.
9. Jetson: reuse `/opt` venv, add `open3d-unofficial-arm`; run with nvidia
   runtime + graphics caps + USB/X11 mounts; prefer the legacy viewer.

---

## 12. Known limitations / next steps

- **2.5D only:** a single frame captures camera-facing surfaces; rotating shows a
  thin shell. Full 3D needs **multi-view fusion**.
- **Non-metric geometry:** placeholder intrinsics. Wire `CalibReadDepthIntrinsic`
  for true fx/fy/cx/cy.
- **Nice-to-haves:** live confidence trackbar; publish depth as a ROS 2
  `PointCloud2` (`rclpy` + `cv_bridge`) for the amazing_hand stack; live 3D view
  (feed frames straight into Open3D).

---

Maintainer: Vishal Agrawal · Stakeholder: Theo Kersjes (onsemi)
