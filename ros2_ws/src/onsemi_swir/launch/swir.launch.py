import os

from ament_index_python.packages import get_package_share_directory


from launch import LaunchDescription, LaunchContext
from launch.actions import IncludeLaunchDescription, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.actions import DeclareLaunchArgument, RegisterEventHandler
from launch.actions import RegisterEventHandler
from launch.event_handlers import OnProcessStart
from launch.substitutions import Command, FindExecutable, PathJoinSubstitution, LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


package_name='onsemi_swir'

def generate_launch_description():

    ld = LaunchDescription()
    swir_node = Node(
        package= package_name,
        executable="swir_node"
    )

    ld.add_action(swir_node)
    return ld


