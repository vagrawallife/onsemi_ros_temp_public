#!/usr/bin/env python3

import argparse
import threading
import time
import sys
import asyncio
import moteus

try:
    import rclpy
    from rclpy.node import Node
    from std_msgs.msg import Float32
except Exception:
    print("rclpy and ROS2 must be available to run this node.", file=sys.stderr)
    raise


class PosSensorPublisher(Node):
    def __init__(self, topic: str = 'pos_sensors', period_s: float = 1.0):
        super().__init__('pos_sensor_node')
        #self.serial_port = serial.Serial(DEFAULT_PORT, DEFAULT_BAUD, timeout=1.0)
        self.pub = self.create_publisher(Float32, topic, 10)
        self.timer = self.create_timer(period_s, self._on_timer)
        self.get_logger().info(f"Publishing on '{topic}' every {period_s}s")

        asyncio.run(self.send_moteus_init())
        asyncio.run(self.send_moteus_stop())

    def _on_timer(self):
        #asyncio.run(self.send_moteus_query(self.m20))
        msg = Float32()
        msg.data = float(97.4)
        self.pub.publish(msg)


    async def send_moteus_init(self):

        self.target_position = moteus.Fdcanusb()
        self.m11 = moteus.Controller(id=11, transport= self.target_position )
        self.m12 = moteus.Controller(id=12, transport= self.target_position )
        self.m13 = moteus.Controller(id=13, transport= self.target_position )
        self.m14 = moteus.Controller(id=14, transport= self.target_position )
        self.m15 = moteus.Controller(id=15, transport= self.target_position )
        self.m20 = moteus.Controller(id=20, transport= self.target_position )
        self.m21 = moteus.Controller(id=21, transport= self.target_position )
        self.get_logger().info(f"Motor init complete: ")

    async def send_moteus_stop(self):
    
        state = await self.m11.set_stop()
        state = await self.m12.set_stop()
        state = await self.m13.set_stop()
        state = await self.m14.set_stop()
        state = await self.m15.set_stop()
        state = await self.m20.set_stop()
        state = await self.m21.set_stop()
        self.get_logger().info(f"Motors stopped: ")

    async def send_moteus_query(self,motor):
        motor_pos = await motor.query()
        await asyncio.sleep(0.1)
        x = motor_pos.values[moteus.Register.POSITION]
        self.get_logger().info(f"Motor position: {x:.2f}")
        msg = Float32()
        msg.data = float(x)
        self.pub.publish(msg)
        


    async def send_moteus_pos(self, position):
        # Quick helper to command position through python api
        p = moteus.PositionMode()
        res = await self.controller.set_position(position=position)
        if res:
            self.get_logger().debug(f"Current Position: {res.values.position}")


def main(argv=None):
    rclpy.init()

    node = PosSensorPublisher(topic='pos_sensors', period_s=1.0)

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