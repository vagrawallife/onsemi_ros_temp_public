from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import TimerAction

def generate_launch_description():
    corner_led_node = Node(
        package='onsemi_lights',
        executable='corner_led',
        name='corner_led',
        output='screen',
        parameters=[{'port': '/dev/onsemi_corner'}]
    )

    lights_node = TimerAction(
        period=3.0,  # Wait 3 seconds before launching
        actions=[
            Node(
                package='onsemi_lights',
                executable='lights_node',
                name='lights_node',
                output='screen'
            )
        ]
    )

    return LaunchDescription([
        corner_led_node,
        lights_node
    ])

