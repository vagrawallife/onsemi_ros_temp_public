import os,tempfile,time,rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import CompressedImage
class Bridge(Node):
 def __init__(self):
  super().__init__('frame_bridge');self.declare_parameter('input_topic',os.getenv('GEMMA_RGB_TOPIC','/sensor/image_raw/compressed'));self.path='/tmp/gemma/latest.jpg';os.makedirs('/tmp/gemma',exist_ok=True);self.warn=0.;self.create_subscription(CompressedImage,self.get_parameter('input_topic').value,self.cb,qos_profile_sensor_data)
 def cb(self,m):
  d=bytes(m.data)
  if len(d)<1024 or not d.startswith(b'\xff\xd8'):
   if time.monotonic()-self.warn>5:self.get_logger().warning('Ignoring non-JPEG compressed frame');self.warn=time.monotonic()
   return
  fd,t=tempfile.mkstemp(dir='/tmp/gemma',suffix='.jpg')
  try:
   with os.fdopen(fd,'wb') as f:f.write(d);f.flush();os.fsync(f.fileno())
   os.replace(t,self.path)
  finally:
   if os.path.exists(t):os.unlink(t)
def main(args=None):
 rclpy.init(args=args);n=Bridge()
 try:rclpy.spin(n)
 except KeyboardInterrupt:pass
 finally:n.destroy_node();rclpy.shutdown()
