import rclpy
from rclpy.node import Node
import time
import json

ON = 1
OFF = 0

class LedDriver(Node):
    reverse = False
    turnBL = OFF
    turnBR = OFF
    brakeBL = ON
    brakeBR = ON
    headBL = OFF
    headBR = OFF
    headFR = ON
    headFL = ON
    brakeFR = OFF
    brakeFL = OFF
    turnFR = OFF
    turnFL = OFF

    def __init__(self, mode="LED Driver", port="/dev/onsemi_leds"):
        super().__init__("led_node", use_global_arguments=False)
        self.port = port
        self.mode = mode
        self.device_connected = False
        self.serialport = None  # Serial communication is off
        self.initialize(mode)

    def initialize(self, mode):
        # Skip actual serial communication
        time.sleep(0.1)
        self.set_lights()

    def setupArray(self):
        if self.reverse:
            return [self.turnBL, self.turnBR, self.brakeFL, self.brakeFR, 
                    self.headFL, self.headFR, self.headBR, self.headBL, 
                    self.brakeBR, self.brakeBL, self.turnFR, self.turnFL]
        else:
            return [self.turnBL, self.turnBR, self.brakeBL, self.brakeBR, 
                    self.headBL, self.headBR, self.headFR, self.headFL, 
                    self.brakeFR, self.brakeFL, self.turnFR, self.turnFL]

    def set_lights(self):
        # Simulate setting lights without serial output
        array = self.setupArray()
        jsonCmd = {
            "cmd": "led_out_en",
            "payload": {
                "values": array
            }
        }
        string_out = json.dumps(jsonCmd) + "\n"
        self.query(string_out)

    def debug_query(self):
        user_input = input("Enter JSON command string:\n")
        string_out = user_input.strip() + "\n"
        return self.query(string_out)

    def query(self, dataOut):
        # Serial communication is disabled
        return "query ignored (serial disabled)"

    def stop(self):
        self.turnBL = self.turnBR = self.turnFL = self.turnFR = OFF
        self.headBL = self.headBR = self.headFL = self.headFR = OFF
        self.brakeFL = self.brakeFR = self.brakeBL = self.brakeBR = ON

        jsonCmd = {
            "cmd": "led_out_en",
            "payload": {
                "values": [OFF, OFF, ON, ON, OFF, OFF, OFF, OFF, ON, ON, OFF, OFF]
            }
        }

        string_out = json.dumps(jsonCmd) + "\n"
        self.query(string_out)
        time.sleep(0.1)
        self.set_lights()
