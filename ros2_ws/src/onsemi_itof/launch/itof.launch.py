import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare

def generate_launch_description():
    itof_params = PathJoinSubstitution([FindPackageShare('onsemi_itof'), 'config', 'itof_params.yaml'])

    ld = LaunchDescription()
    ld.add_action(DeclareLaunchArgument('use_sim_time', default_value='false'))
    ld.add_action(Node(
        package='onsemi_itof', 
        executable='itof_publisher', 
        name='itof_publisher',
        namespace='itof', 
        output='screen',
        parameters=[itof_params, {'use_sim_time': LaunchConfiguration('use_sim_time')}]))
    #ld.add_action(Node(
    #        package='tf2_ros', executable='static_transform_publisher',
    #        name='itof_static_tf', output='screen',
    #        arguments=[
    #            '--x', '0.0', '--y', '0.0', '--z', '0.0',
    #            '--qx', '0.7071', '--qy', '0.0', '--qz', '0.0', '--qw', '0.7071',
    #            '--frame-id', 'head_1',
    #            '--child-frame-id', 'itof_optical_frame',
    #        ]))
    return ld
