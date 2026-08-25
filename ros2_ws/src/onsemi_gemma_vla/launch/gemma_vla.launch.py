import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument,ExecuteProcess,TimerAction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
def generate_launch_description():
 topic=LaunchConfiguration('rgb_topic')
 bridge=Node(package='onsemi_gemma_vla',executable='frame_bridge',output='screen',parameters=[{'input_topic':topic}])
 backend=ExecuteProcess(cmd=['/usr/local/bin/llama-server','--model','/models/gemma-4-E2B-it-Q4_K_M.gguf','--mmproj','/models/mmproj-gemma4-e2b-f16.gguf','--host','127.0.0.1','--port','8080','--ctx-size','2048','--parallel','1','--flash-attn','on','--n-gpu-layers','99'],output='screen')
 client=TimerAction(period=12.0,actions=[ExecuteProcess(cmd=['gemma-vla-client'],output='screen',emulate_tty=True,additional_env={'FRAME_PATH':'/tmp/gemma/latest.jpg','LLAMA_URL':'http://127.0.0.1:8080/v1/chat/completions'})])
 return LaunchDescription([DeclareLaunchArgument('rgb_topic',default_value=os.getenv('GEMMA_RGB_TOPIC','/sensor/image_raw/compressed')),bridge,backend,client])
