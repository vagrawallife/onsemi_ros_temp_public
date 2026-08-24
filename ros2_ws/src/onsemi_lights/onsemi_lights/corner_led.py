import rclpy
from rclpy.node import Node
from std_msgs.msg import String
import serial
import time

class CornerLED(Node):
    def __init__(self):
        super().__init__('corner_led')
        self.serialport = None
        self.port = self.declare_parameter('port', '/dev/onsemi_corner').get_parameter_value().string_value

        try:
            self.serialport = serial.Serial(port=self.port, baudrate=115200, timeout=1)
            self.get_logger().info(f"Serial port {self.port} initialized.")
        except serial.SerialException as e:
            self.get_logger().error(f"Serial exception: {e}")
            return

        self.i2c_setup()
        self.subscription = self.create_subscription(
            String,
            'corner_led/command',
            self.receive_command,
            10
        )

        self.get_logger().info("[CornerLED] Ready: serial and I2C initialized.")

    def i2c_setup(self):
        commands = [
            b'get ver\r\n',
            b'set I2C1CONF\r\n',
            b'set I2C1SPEED=1\r\n',
            b'set I2C1DATA=6004C000DFFF\r\n',
            b'set I2C1DATA=6005C002010FFF\r\n',
        ]
        for cmd in commands:
            try:
                self.serialport.write(cmd)
                self.get_logger().info(f"[Init] Sent: {cmd.decode().strip()}")
                time.sleep(0.5)
                if self.serialport.in_waiting:
                    reply = self.serialport.readline().decode('utf-8').strip()
                    self.get_logger().info(f"[Init] Reply: {reply}")
            except Exception as e:
                self.get_logger().warn(f"I2C setup failed: {e}")

    def receive_command(self, msg):
        command = msg.data.strip()
        if self.serialport and self.serialport.is_open:
            try:
                self.serialport.write(f"{command}\r\n".encode())
                self.get_logger().info(f"[Command] Sent: {command}")
                time.sleep(0.1)
                if self.serialport.in_waiting:
                    reply = self.serialport.readline().decode().strip()
                    self.get_logger().info(f"[Command] Reply: {reply}")
            except Exception as e:
                self.get_logger().error(f"[Command] Serial error: {e}")

    def send_shutdown_command(self):
        if self.serialport and self.serialport.is_open:
            try:
                
                self.serialport.write(b'set I2C1DATA=6004C0004FFF\r\n')
                time.sleep(0.5)
                if self.serialport.in_waiting:
                    reply = self.serialport.readline().decode().strip()
                    self.get_logger().info(f"Shutdown reply: {reply}")
            except Exception as e:
                self.get_logger().error(f"Shutdown command failed: {e}")

def main(args=None):
    rclpy.init(args=args)
    node = CornerLED()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass  
    finally:
        if node.serialport:
            node.send_shutdown_command()
            node.serialport.close()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()

if __name__ == '__main__':
    main()
