import os
from ament_index_python.packages import get_package_share_directory


from launch import LaunchDescription, LaunchContext
from launch.actions import IncludeLaunchDescription, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, FindExecutable, PathJoinSubstitution, LaunchConfiguration
from launch.actions import DeclareLaunchArgument, RegisterEventHandler
from launch.event_handlers import OnProcessStart
from launch.event_handlers import OnProcessExit
from launch.conditions import IfCondition
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
from launch.actions import ExecuteProcess
from launch.actions import LogInfo
from launch_ros.parameter_descriptions import ParameterValue

def generate_launch_description():



    # Initialize Arguments
    gui = LaunchConfiguration("gui")
    use_mock_hardware = LaunchConfiguration("use_mock_hardware")
    use_sim_time = LaunchConfiguration('use_sim_time')
    sim_mode = LaunchConfiguration('sim_mode')
    use_ros2_control = LaunchConfiguration('use_ros2_control')
    

    # Declare arguments
    declared_arguments = []
    declared_arguments.append( DeclareLaunchArgument( name="gui", default_value="true", description="Start RViz2 automatically with this launch file.",  ))
    declared_arguments.append( DeclareLaunchArgument( name="use_mock_hardware", default_value="false", description="Start robot with mock hardware mirroring command to its states.", ))
    declared_arguments.append( DeclareLaunchArgument( name="use_sim_time", default_value="false", description="Sim time for gazibo use.", ))
    declared_arguments.append( DeclareLaunchArgument( name="sim_mode", default_value="false", description="Sim mode for gazibo use.", ))
    declared_arguments.append( DeclareLaunchArgument( name="use_ros2_control", default_value="true", description="ros2 controller use.", ))


    context = LaunchContext()
   
    package_name='onsemi_amr' 

    onsemi_cem102 = IncludeLaunchDescription(
            PythonLaunchDescriptionSource([os.path.join(
                get_package_share_directory('onsemi_cem102'),'launch','onsemi_cem102.launch.py'
            )]), launch_arguments={'use_sim_time': use_sim_time}.items())   

    onsemi_pos = IncludeLaunchDescription(
            PythonLaunchDescriptionSource([os.path.join(
                get_package_share_directory('onsemi_pos'),'launch','onsemi_pos.launch.py'
            )]), launch_arguments={'use_sim_time': use_sim_time}.items())   


    camera = IncludeLaunchDescription(
            PythonLaunchDescriptionSource([os.path.join(
                get_package_share_directory('onsemi_camera'),'launch','camera.launch.py'
            )]), launch_arguments={'use_sim_time': use_sim_time}.items())     
    
    itof = IncludeLaunchDescription(
            PythonLaunchDescriptionSource([os.path.join(
                get_package_share_directory('onsemi_itof'),'launch','itof.launch.py'
            )]), launch_arguments={'use_sim_time': use_sim_time}.items())

    joystick = IncludeLaunchDescription(
            PythonLaunchDescriptionSource([os.path.join(
                get_package_share_directory('onsemi_control'),'launch','joystick.launch.py'
                #get_package_share_directory('onsemi_control'),'launch','joystickm.launch.py'
            )]), launch_arguments={'use_sim_time': use_sim_time }.items())   

    laser_box_filter = IncludeLaunchDescription(
                PythonLaunchDescriptionSource([os.path.join(
                    get_package_share_directory('laser_filters'),'examples','box_filter_example.launch.py'
            )]), launch_arguments={'use_sim_time': use_sim_time}.items())



    camera_transform = Node(
            package='image_transport',
            executable='republish',
            name='camera_transform_node',
            namespace='sensor',
            arguments=['compressed'],
            remappings=[
                ('in/compressed', 'image_raw/compressed'),
                ('out', 'camera/image_raw/uncompressed')]
    )

    twist_mux_params = os.path.join(get_package_share_directory('onsemi_control'),'config','twist_mux.yaml')
    twist_mux = Node(
            package='twist_mux',
            executable='twist_mux',
            name='twist_mux',
            parameters=[twist_mux_params],
            #remappings=[('/cmd_vel_out','/diff_drive_controller/cmd_vel_unstamped')]
            #remappings=[('/cmd_vel_out','/diff_ cont/cmd_vel_unstamped')]
        )

 
    #robot_description = Command(['ros2 param get --hide-type /robot_state_publisher robot_description'])

    
    # Get URDF via xacro
    robot_description_content = Command(
        [
            PathJoinSubstitution([FindExecutable(name="xacro")]),
            " ",
            PathJoinSubstitution(
                [
                    FindPackageShare("onsemi_amr"), 
                    "description/urdf/onsemi_urdf",
                    "sim_onsemi.xacro"
                ]
            ),
            " ", "use_mock_hardware:=", use_mock_hardware, 
            " ", "sim_mode:=", sim_mode, 
            " ", "use_ros2_control:=", use_ros2_control,
            " ", "use_sim_time:=", use_sim_time,
        ]
    )
    robot_description = {"robot_description": robot_description_content,'use_sim_time': use_sim_time}
    robot_controllers = PathJoinSubstitution(
        [ 
            FindPackageShare("onsemi_amr"), 
            "config", 
            "onsemi_controllers.yaml", 
        ]
    )
    control_node = Node(
        package="controller_manager",
        executable="ros2_control_node",
        parameters=[robot_description, robot_controllers],
        output="both",
    )
    robot_state_pub_node = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        output="both",
        parameters=[robot_description],
        #remappings=[("/diff_drive_controller/cmd_vel_unstamped", "/cmd_vel_joy"),
        # remappings=[("/diff_cont/cmd_vel_unstamped", "/cmd_vel_joy"),],
    )
    joint_state_pub_node = Node(
        package="joint_state_publisher",
        executable="joint_state_publisher",
        output="both",
        parameters=[robot_description],
    )
    joint_state_broadcaster_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["joint_broad", "--controller-manager", "/controller_manager"],
    )
    robot_controller_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["diff_cont", "--controller-manager", "/controller_manager"],
    )

    rviz_config_file = PathJoinSubstitution(
        [FindPackageShare("onsemi_amr"), "config", "amr_onsemi.rviz"]
    )

    rviz_node = Node(
        package="rviz2",
        executable="rviz2",
        name="rviz2",
        output="log",
        arguments=["-d", rviz_config_file]
    )
    #foxglove_bridge = ExecuteProcess(cmd=["ros2 launch foxglove_bridge foxglove_bridge_launch.xml"])
    #ros2 launch foxglove_bridge foxglove_bridge_launch.xml
    foxglove_node = Node(
        package="foxglove_bridge",
        executable="foxglove_bridge",
        name="foxglove_bridge",
        output="log",
        arguments=["foxglove_bridge_launch.xml"]
    )


    nodes = [
        #control_node,
        robot_state_pub_node,
        joint_state_pub_node,
        #joystick,
        #twist_mux,
        onsemi_cem102,
        onsemi_pos,
        camera,
        itof,    
        #rviz_node,
        foxglove_node,
    ]

    return LaunchDescription(declared_arguments + nodes )


