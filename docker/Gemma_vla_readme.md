# Single-container Gemma integration
Merge this folder into the root of onsemi_ros_temp_public.

1. Keep models on the host in ~/models using the exact filenames below.
2. Run: python3 apply_gemma_integration.py
3. Run: cp docker/gemma_vla.env.example docker/gemma_vla.env
4. Edit camera topic, microphone and speaker in docker/gemma_vla.env.
5. Build and run with your existing workflow from docker/.

Models:
- gemma-4-E2B-it-Q4_K_M.gguf
- mmproj-gemma4-e2b-f16.gguf

The updated run_ximage mounts ~/models at /models and passes audio configuration.
ROS remains the only RGB-camera owner. The onsemi_gemma_vla package exports the
latest compressed ROS frame to /tmp/gemma/latest.jpg. The patched VLA reads that
file instead of opening /dev/videoX.

Disable Gemma while keeping all existing nodes:
ros2 launch onsemi_amr launch_robo.launch.py use_gemma_vla:=false
