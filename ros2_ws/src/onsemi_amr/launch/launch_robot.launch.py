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

    rsp = IncludeLaunchDescription(
                PythonLaunchDescriptionSource([os.path.join(
                    get_package_share_directory(package_name),'launch','rsp.launch.py'
                )]), launch_arguments={'use_sim_time': use_sim_time, 'use_ros2_control': use_ros2_control}.items()
    )

    lights = IncludeLaunchDescription(
                PythonLaunchDescriptionSource([os.path.join(
                    get_package_share_directory('onsemi_lights'),'launch','lights.launch.py'
                )]), launch_arguments={'use_sim_time': use_sim_time}.items()
    )
    motor = IncludeLaunchDescription(
                PythonLaunchDescriptionSource([os.path.join(
                    get_package_share_directory('onsemi_control'),'launch','motor.launch.py'
                )]), launch_arguments={'use_sim_time': use_sim_time}.items()
    )  


    slam_toolbox_package_path = FindPackageShare(package="slam_toolbox").find("slam_toolbox")
    # Include the online_async launch file
    #slam_toolbox_launch_file = os.path.join(get_package_share_directory("onsemi_amr"), 'config', 'mapper_params_online_async.yaml')
    slam_toolbox_launch_file = os.path.join(slam_toolbox_package_path, "launch", "online_async_launch.py")
    
    #slam = IncludeLaunchDescription(       launch_descripter = slam_toolbox_launch_file)  
    #slam = Node( 
    #       package = "slam_toolbox",
    #        executable="twist_mux",
    #        parameters=[twist_mux_params],
    #)  

    slam = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([os.path.join(
                    get_package_share_directory('onsemi_amr'),'launch','online_async_launch.py'
                )]),
        launch_arguments={'use_sim_time': use_sim_time}.items())
    
    nav2 = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([os.path.join(
                    get_package_share_directory('onsemi_amr'),'launch','navigation_launch.py'
                )]),
        launch_arguments={'use_sim_time': use_sim_time}.items())




    print ("AMR with s2 lidar, See3CAM_24CUG AR0234, xbox control ")
    sllidar = IncludeLaunchDescription( PythonLaunchDescriptionSource([os.path.join(
            get_package_share_directory('sllidar_ros2'),'launch','sllidar_s2_launch.py'
            #get_package_share_directory('sllidar_ros2'),'launch','sllidar_a2m8_launch.py'
            #get_package_share_directory('sllidar_ros2'),'launch','sllidar_a3_launch.py'
            )]), launch_arguments={'use_sim_time': use_sim_time}.items())
    camera = IncludeLaunchDescription(
            PythonLaunchDescriptionSource([os.path.join(
                get_package_share_directory('onsemi_camera'),'launch','camera.launch.py'
                #get_package_share_directory('onsemi_camera'),'launch','camera_stereo.launch.py'
                #get_package_share_directory('onsemi_camera'),'launch','cameravci.launch.py'
            )]), launch_arguments={'use_sim_time': use_sim_time}.items())     
    joystick = IncludeLaunchDescription(
            PythonLaunchDescriptionSource([os.path.join(
                get_package_share_directory('onsemi_control'),'launch','joystick.launch.py'
                #get_package_share_directory('onsemi_control'),'launch','joystickm.launch.py'
            )]), launch_arguments={'use_sim_time': use_sim_time }.items())   

    laser_box_filter = IncludeLaunchDescription(
                PythonLaunchDescriptionSource([os.path.join(
                    get_package_share_directory('laser_filters'),'examples','box_filter_example.launch.py'
                )]), launch_arguments={'use_sim_time': use_sim_time}.items()
    )



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


    demo = IncludeLaunchDescription(
                PythonLaunchDescriptionSource([os.path.join(
                    get_package_share_directory('onsemi_demo'),'launch','demo.launch.py'
                )]), launch_arguments={'use_sim_time': use_sim_time}.items()
    )
    ball_tracker = IncludeLaunchDescription(
                PythonLaunchDescriptionSource([os.path.join(
                    get_package_share_directory('onsemi_amr'),'launch','ball_tracker.launch.py'
                )]), launch_arguments={'use_sim_time': use_sim_time}.items()
    )

    fiducial = IncludeLaunchDescription(
                PythonLaunchDescriptionSource([os.path.join(
                    get_package_share_directory('onsemi_fiducial'),'launch','fiducial.launch.py'
                )]), launch_arguments={'use_sim_time': use_sim_time}.items()
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

    #foxglove_bridge = ExecuteProcess(cmd=["ros2 launch foxglove_bridge foxglove_bridge_launch.xml"])

    #robot_description = Command(['ros2 param get --hide-type /robot_state_publisher robot_description'])
    
    #ThK
    
    # Get URDF via xacro
    robot_description_content = Command(
        [
            PathJoinSubstitution([FindExecutable(name="xacro")]),
            " ",
            PathJoinSubstitution(
                [
                    FindPackageShare("onsemi_amr"), 
                    "description/robots",
                    "robot.urdf.xacro"
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
        remappings=[("/diff_drive_controller/cmd_vel_unstamped", "/cmd_vel_joy"),
        # remappings=[("/diff_cont/cmd_vel_unstamped", "/cmd_vel_joy"),
        ],
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
    #rviz_config_file = PathJoinSubstitution(
    #    [FindPackageShare("hesai_ros_driver"), "rviz", "rviz2.rviz"]
    #)
   

    rviz_node = Node(
        package="rviz2",
        executable="rviz2",
        name="rviz2",
        output="log",
        arguments=["-d", rviz_config_file]
    )
    #ros2 launch foxglove_bridge foxglove_bridge_launch.xml
    foxglove_node = Node(
        package="foxglove_bridge",
        executable="foxglove_bridge",
        name="foxglove_bridge",
        output="log",
        arguments=["foxglove_bridge_launch.xml"]
    )

    # Delay rviz start after `joint_state_broadcaster`
    delay_rviz_after_joint_state_broadcaster_spawner = RegisterEventHandler(
        event_handler=OnProcessExit(
            target_action=joint_state_broadcaster_spawner,
            on_exit=[rviz_node],
        )
    )

    # Delay start of robot_controller after `joint_state_broadcaster`
    delay_robot_controller_spawner_after_joint_state_broadcaster_spawner = RegisterEventHandler(
        event_handler=OnProcessExit(
            target_action=joint_state_broadcaster_spawner,
            on_exit=[robot_controller_spawner],
        )
    )

    # delay_rplidar = RegisterEventHandler(
    #     event_handler=OnProcessExit(
    #         target_action=rplidar,
    #         on_exit=[lights],
    #     )
    # )
    # delay_laser_filter = RegisterEventHandler(
    #     event_handler=OnProcessExit(
    #         target_action=laser_box_filter,
    #         on_exit=[delay_rplidar],
    #     )
    # )

    nodes = [
        control_node,
        robot_state_pub_node,
        #joint_state_broadcaster_spawner,
        #delay_rviz_after_joint_state_broadcaster_spawner,
        #delay_robot_controller_spawner_after_joint_state_broadcaster_spawner,   
        #rsp,
        joystick,
        twist_mux,
        lights,
        #roboclaw,
        motor,
        sllidar,
        laser_box_filter,
        camera,    
        demo,
        fiducial,
        rviz_node,
        #foxglove_node,
        slam,
        #nav2,
        #camera_transform, 
    ]

    return LaunchDescription(declared_arguments + nodes )


    #ThK
    #delayed_controller_manager = TimerAction(period=3.0, actions=[controller_manager])

    # Run the spawner node from the gazebo_ros package. The entity name doesn't really matter if you only have a single robot.
    #spawn_entity = Node(package='gazebo_ros', executable='spawn_entity.py',
    #                     arguments=['-topic', 'robot_description',
    #                                '-entity', 'my_bot'],
    #                     output='screen')


