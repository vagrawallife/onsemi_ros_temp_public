import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Joy
from std_msgs.msg import String
from onsemi_lights.matrix_driver import MatrixDriver
import time
import threading

class LightControl(Node):
    def __init__(self):
        super().__init__('light_node')
        self.publisher = self.create_publisher(String, 'corner_led/command', 10)
        self.matrix = MatrixDriver()

        self.left_blinker_active = False
        self.right_blinker_active = False
        self.left_blinker_thread = None
        self.right_blinker_thread = None

        self.last_command_time = time.time()
        self.default_timeout = 10.0
        self.first_start = True

        self.create_subscription(Joy, 'joy', self.joy_callback, 5)
        self.statePub = self.create_publisher(String, 'state', 1)
        self.stateSub = self.create_subscription(String, 'state', self.stateCallback, 10)

        self.command_map = {
            "off": "set I2C1DATA=600EC003000000000000000000000000",
            "F": "set I2C1DATA=600EC003007F00007F007F7F7F7F7F7F7F",
            "B": "set I2C1DATA=600EC0037F7F7F7F7F7F007F00007F00",
            "white": "set I2C1DATA=600EC0037F7F7F7F7F7F7F7F7F7F7F7F",
            "red": "set I2C1DATA=600EC003007F00007F00007F00007F00",
            "blinker": "set I2C1DATA=600EC003507F00507F00507F00507F00",
            "L": [
                "set I2C1DATA=600EC003007F00507F007F7F7F507F00",
                "set I2C1DATA=600EC003007F000000007F7F7F000000"
            ],
            "R": [
                "set I2C1DATA=600EC003507F00007F00507F007F7F7F",
                "set I2C1DATA=600EC003000000007F000000007F7F7F"
            ],
            "O": "set I2C1DATA=600EC003007F00007F007F7F7F7F7F7F7F",
        }

        self.declare_parameter('default_symbol', 'O')
        default_symbol = self.get_parameter('default_symbol').get_parameter_value().string_value
        self.set_feedback(default_symbol)

        self.matrix.state = "teleop"
        self.matrix.msg.data = self.matrix.state
        self.statePub.publish(self.matrix.msg)

        self.create_timer(1.0, self.check_default_timeout)

    def run_blinker(self, side):
        frames = self.command_map["L"] if side == "left" else self.command_map["R"]
        symbol = "L" if side == "left" else "R"
        self.matrix.setContent(symbol)
        i = 0
        while getattr(self, f"{side}_blinker_active"):
            self.last_command_time = time.time() 
            msg = String()
            msg.data = frames[i % 2]
            self.publisher.publish(msg)
            time.sleep(1.0)
            i += 1

    def joy_callback(self, joy_msg):
        old_state = self.matrix.state

        mode_buttons = {
            0: ("teleop", "G"),
            1: ("demo", "R"),
            3: ("charge", "B"),
            4: ("follow", "P")
        }

        for btn, (state, border) in mode_buttons.items():
            if btn < len(joy_msg.buttons) and joy_msg.buttons[btn] == 1 and self.matrix.currentBorder != border:
                self.matrix.state = state
                self.matrix.setBorder(border)
                self.get_logger().info(f"Border set to: {border}")
                self.last_command_time = time.time() 

        axes = joy_msg.axes
        joy_x = axes[1] if len(axes) > 1 else 0.0
        joy_y = axes[0] if len(axes) > 0 else 0.0

        enable_button_held = len(joy_msg.buttons) > 6 and joy_msg.buttons[6] == 1
        turbo_button_held = len(joy_msg.buttons) > 7 and joy_msg.buttons[7] == 1

        if enable_button_held or turbo_button_held:
            self.last_command_time = time.time()  

            if joy_y > 0.2 and not self.left_blinker_active:
                self.left_blinker_active = True
                self.left_blinker_thread = threading.Thread(target=self.run_blinker, args=("left",), daemon=True)
                self.left_blinker_thread.start()
            elif joy_y <= 0.2:
                self.left_blinker_active = False

            if joy_y < -0.2 and not self.right_blinker_active:
                self.right_blinker_active = True
                self.right_blinker_thread = threading.Thread(target=self.run_blinker, args=("right",), daemon=True)
                self.right_blinker_thread.start()
            elif joy_y >= -0.2:
                self.right_blinker_active = False

            if not self.left_blinker_active and not self.right_blinker_active:
                direction = None
                if joy_x > 0.1:
                    direction = "F"
                elif joy_x < -0.1:
                    direction = "B"

                if direction:
                    self.set_feedback(direction)
                    self.last_command_time = time.time() 

        else:
            self.left_blinker_active = False
            self.right_blinker_active = False

        if self.matrix.state != old_state:
            self.matrix.msg.data = self.matrix.state
            self.statePub.publish(self.matrix.msg)

    def check_default_timeout(self):
        default_symbol = self.get_parameter('default_symbol').get_parameter_value().string_value
        if time.time() - self.last_command_time > self.default_timeout:
            self.set_feedback(default_symbol)

    def stateCallback(self, msg):
        self.matrix.state = msg.data
        border_colors = {
            "teleop": "G", "demo": "R", "charge": "B", "follow": "P"
        }
        if msg.data in border_colors:
            border = border_colors[msg.data]
            self.matrix.setBorder(border)
            self.get_logger().info(f"Border set to: {border}")
            self.last_command_time = time.time()  

    def set_feedback(self, symbol):
        if not self.first_start and self.matrix.currentContent == symbol:
            return
        self.matrix.setContent(symbol)
        self.send_corner_led_command(symbol)
        self.get_logger().info(f"Symbol displayed: '{symbol}'")
        self.first_start = False

    def send_corner_led_command(self, symbol):
        self.last_command_time = time.time()  
        cmd_entry = self.command_map.get(symbol)
        if not cmd_entry:
            return
        cmds = cmd_entry if isinstance(cmd_entry, list) else [cmd_entry]
        for cmd in cmds:
            msg = String()
            msg.data = cmd
            self.publisher.publish(msg)
            time.sleep(0.1)

    def stop(self):
        self.left_blinker_active = False
        self.right_blinker_active = False
        if self.matrix:
            self.matrix.stop()

def main(args=None):
    rclpy.init(args=args)
    node = LightControl()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.stop()
        node.destroy_node()
        rclpy.try_shutdown()

if __name__ == '__main__':
    main()
