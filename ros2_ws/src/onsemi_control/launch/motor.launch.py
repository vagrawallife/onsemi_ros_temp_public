from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        Node(
            name='onsemi_motor_node',
            package='onsemi_control',
            executable='onsemi_motor_node',
            output='screen',
        ),
    ])
