#!/usr/bin/env bash
set -euo pipefail
xhost +local:root
XAUTH=/tmp/.docker.xauth
HERE="$(cd "$(dirname "$0")" && pwd)"
ENV_FILE="${HERE}/gemma_vla.env"
[[ -f "$ENV_FILE" ]] || cp "${ENV_FILE}.example" "$ENV_FILE"
set -a; source "$ENV_FILE"; set +a
xauth_list="$(xauth nlist :0 2>/dev/null | tail -n 1 | sed -e 's/^..../ffff/' || true)"
if [[ ! -f "$XAUTH" ]]; then [[ -n "$xauth_list" ]] && printf '%s\n' "$xauth_list" | xauth -f "$XAUTH" nmerge - || touch "$XAUTH"; chmod a+r "$XAUTH"; fi
mkdir -p "$HOME/depthvista_captures" "$HOME/models"
docker run -it --rm --name=onsemi_jazzy_arm64_container --runtime=nvidia --env="DISPLAY=$DISPLAY" --env="QT_X11_NO_MITSHM=1" --env="XAUTHORITY=$XAUTH" --env="PULSE_SERVER=unix:/run/user/$(id -u)/pulse/native" --env="MIC_DEVICE=$MIC_DEVICE" --env="SPK_DEVICE=$SPK_DEVICE" --env="VOICE=$VOICE" --env="GEMMA_RGB_TOPIC=$GEMMA_RGB_TOPIC" --env="ROS_DOMAIN_ID=$ROS_DOMAIN_ID" --env="RMW_IMPLEMENTATION=$RMW_IMPLEMENTATION" --volume="/tmp/.X11-unix:/tmp/.X11-unix:rw" --volume="$XAUTH:$XAUTH:rw" --volume="/run/user/$(id -u)/pulse:/run/user/$(id -u)/pulse" --volume="$HOME/.config/pulse/cookie:/root/.config/pulse/cookie:ro" --volume="$HOME/.cache/huggingface:/root/.cache/huggingface" --volume="$HOME/models:/models:ro" --mount="type=bind,source=${HERE}/../ros2_ws,target=/home/onsemi/onsemi_ros/ros2_ws" --network=host --volume=/dev:/dev --volume="$HOME/depthvista_captures:/opt/depthvista/captures" --ipc=host --privileged --device=/dev/input --device=/dev/snd --workdir=/home/onsemi/onsemi_ros/ros2_ws onsemi_jazzy bash
