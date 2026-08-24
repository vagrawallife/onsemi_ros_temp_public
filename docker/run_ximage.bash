
xhost +local:root
#sudo xhost +si:localuser:root
XAUTH=/tmp/.docker.xauth

 echo "Preparing Xauthority data..."
 xauth_list=$(xauth nlist :0 | tail -n 1 | sed -e 's/^..../ffff/')
 if [ ! -f $XAUTH ]; then
     if [ ! -z "$xauth_list" ]; then
         echo $xauth_list | xauth -f $XAUTH nmerge -
     else
        touch $XAUTH
     fi
     chmod a+r $XAUTH
 fi

echo "Done."
echo ""
echo "Verifying file contents:"
file $XAUTH
echo "--> It should say \"X11 Xauthority data\"."
echo ""
echo "Permissions:"
ls -FAlh $XAUTH
echo ""
echo "Running docker..."

docker run -it --rm \
    --name=onsemi_jazzy_arm64_container\
    --runtime nvidia \
    --env="DISPLAY=$DISPLAY" \
    --env="QT_X11_NO_MITSHM=1" \
    --volume="/tmp/.X11-unix:/tmp/.X11-unix:rw" \
    --env="XAUTHORITY=$XAUTH" \
    --volume="$XAUTH:$XAUTH" \
    --mount type=bind,source="$(pwd)"/ros2_ws,target=/home/onsemi/onsemi_ros/ros2_ws \
    --net=host -v /dev:/dev \
    -v $HOME/depthvista_captures:/opt/depthvista/captures \
    --ipc=host \
    --privileged \
    --device=/dev/input\
    --workdir=/home/onsemi/onsemi_ros/ros2_ws \
    onsemi_jazzy \
    bash