#!/usr/bin/env python3
"""
ROS2 publisher for CEM102/Gas sensor values.
Reads serial CSV lines, parses the configured value column, converts PPB->PPM,
and publishes the latest reading every 0.5 seconds on `/gas_sensor_ppm`.

Usage:
  python3 gas_sensor_ros2.py --port /dev/ttyUSB0 --baud 9600

Requires: rclpy, pyserial, std_msgs
"""

import argparse
import threading
import time
import sys


try:
    import serial
except Exception as e:
    print("pyserial is required: pip install pyserial", file=sys.stderr)
    raise

try:
    import rclpy
    from rclpy.node import Node
    from std_msgs.msg import Float32
except Exception:
    print("rclpy and ROS2 must be available to run this node.", file=sys.stderr)
    raise

# Parse config similar to Gas_Sensor_Comp.py
PPB_TO_PPM = 1000.0
DEFAULT_PORT = "/dev/ttyCH341USB0"
DEFAULT_BAUD = 230400
VALUE_IDX_A = 3       # whitespace col — WE2 (col 0="-I-", col 1=counter, col 2=val, col 3=WE1, col 4=WE2)
DIVISOR     = 20      # PORT_A value / DIVISOR = PPM
VALUE_IDX_B = 1       # CSV col for PORT_B
PPB_TO_PPM  = 1000.0  # PORT_B raw is PPB

def _parse_csv(self, line, idx):
    if line.startswith("-I-") and len(line) > 3 and not line[3].isspace():
        line = f"-I- {line[3:]}"
        #self.get_logger().info(f"ppm {line}")
    parts = line.strip().split()
    #self.get_logger().info(f"parts {parts[idx]}")
    if len(parts) <= idx:
        return None
    try:
        return float(parts[idx])
    except ValueError:
        return None


class GasSensorPublisher(Node):
    def __init__(self, topic: str = 'gas_sensor_ppm', period_s: float = 0.5):
        super().__init__('cem102_sensor_node')
        self.serial_port = serial.Serial(DEFAULT_PORT, DEFAULT_BAUD, timeout=1.0)
        self.pub = self.create_publisher(Float32, topic, 10)
        self.timer = self.create_timer(period_s, self._on_timer)
        self.get_logger().info(f"Publishing on '{topic}' every {period_s}s")

    def _on_timer(self):
        raw = self.serial_port.readline()  
        ppm = -1.0
        if raw:
            line = raw.decode("utf-8", errors="replace").rstrip()
            val = _parse_csv(self,line, VALUE_IDX_A)
            if val is not None:
                ppm = val / DIVISOR
        #self.get_logger().info(f"last ppm {ppm}")        
        msg = Float32()
        msg.data = float(ppm)
        self.pub.publish(msg)


def main(argv=None):
    rclpy.init()
    node = GasSensorPublisher(topic='gas_sensor_ppm', period_s=0.1)

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.get_logger().info('Shutting down')
        node.destroy_node()
        rclpy.shutdown()
if __name__ == '__main__':
    main()