# Add the iToF node to launch_robo.launch.py (onsemi_amr)

Your repo already uses this pattern: CEM102 and camera are SEPARATE packages,
included via `IncludeLaunchDescription`, and `foxglove_node` is already in the
`nodes` list. So we add `onsemi_itof` the SAME way.

## 1) Put the package + SDK in place
- Extract `onsemi_itof/` into `ros2_ws/src/`.
- The DepthVista SDK is provided by the Docker image at `/opt/depthvista`
  (see onsemi_ros_Dockerfile_final.txt). `config/itof_params.yaml` already
  points `sdk_path` there.

## 2) Edit launch_robo.launch.py  (2 tiny changes)

### (a) Add the include, right AFTER the `camera = IncludeLaunchDescription(...)`:
```python
    itof = IncludeLaunchDescription(
            PythonLaunchDescriptionSource([os.path.join(
                get_package_share_directory('onsemi_itof'),'launch','itof.launch.py'
            )]), launch_arguments={'use_sim_time': use_sim_time}.items())
```

### (b) Add `itof,` to the `nodes` list (next to cem102 / camera):
```python
    nodes = [
        cem102,
        camera,
        itof,          # <-- ADD THIS LINE
        foxglove_node,
    ]
```
`restart.sh` is unchanged (it already runs launch_robo.launch.py; foxglove_node
is already launched, so the iToF topics appear in Foxglove).

## 3) Build + run
```
cd ros2_ws
colcon build --packages-select onsemi_itof
source install/setup.bash
./src/onsemi_amr/restart.sh
```

## Topics
| Topic | Type |
|-------|------|
| /itof/depth/color     | sensor_msgs/Image bgr8  (econ colours) |
| /itof/depth/image_raw | sensor_msgs/Image 16UC1 (mm) |
| /itof/ir/image        | sensor_msgs/Image mono8 |
| /itof/camera_info     | sensor_msgs/CameraInfo  |

## Docker / SDK (important)
- The ROS node runs in the **onsemi_ros** image (NOT amazing_hand), so the SDK
  `.so` must live in THAT image. Use `onsemi_ros_Dockerfile_final.txt` which
  COPYs `DepthVistaViewer/` -> `/opt/depthvista` and sets LD_LIBRARY_PATH.
- Put a `DepthVistaViewer/` folder (with the aarch64 `libDepthVistaSDK.so` +
  dependent `.so` files) in the onsemi_ros **build context** before building.
- USB passthrough for the container (`--privileged -v /dev:/dev`), same as usb_cam.
