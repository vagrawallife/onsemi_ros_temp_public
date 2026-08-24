

import rclpy
from rclpy.node import Node

import sys, os, time
import time
from geometry_msgs.msg import Twist
from geometry_msgs.msg import Quaternion
import signal
import math
import time
from std_msgs.msg import String
import sys
import numpy as np
import random
from std_msgs.msg import Float32




home = {
            "x" : 0.59,
            "y" : 0.0,
            "yaw" : 1.57
        }

center = {
            "x" : 0.0,
            "y" : 0.0,
            "yaw" : 1.57
        }

p1 = {
            "x" : -0.25,
            "y" : -0.25,
            "yaw" : 0
        }

p2 = {
            "x" : -0.25,
            "y" : 0.25,
            "yaw" : 0
        }

class DemoControl(Node):
    blinker = 0
    blink = False
    tic = 0
    toc = 0
    blinkInterval = 0.3
    timerInterval = 0.5
    
    def __init__(self):
        super().__init__("onsemi_demo_node")
        self.get_logger().info("Demo Node ROS2")
        self.y_speed = 0.0
        self.x_speed = 0.0
        self.yaw_speed = 0.0
        self.state = None
        self.demo_state = 0
        self.demo_run = False
        self.turn_speed = 0.2
        self.turn_time = 4
        # subscriber for amr state (charge, teleop, follow, demo)
        self.state_pub = self.create_publisher(String, 'state',1) 
        self.state_sub = self.create_subscription(String, 'state', self.stateCallback, 1)
        # cmd_vel publisher
        self.vel_publisher = self.create_publisher(Twist,'/cmd_vel_nav', 128)
        self.timer = self.create_timer(0.5, self.timerControl)
        #self.timerControl()
        pass

    def stop(self):
        self.update_vel(0,0,0)

    def stateCallback(self, state):
        self.state = state.data
        if(self.state == "demo"):
           if(self.demo_state == 0 ):
                self.get_logger().info(" Start Demo ")
                self.demo_state = 1   
                self.demo_run = True
                self.timer = self.create_timer(0.02, self.timerControl)
        else:
                self.get_logger().info(" Stop Demo ")
                self.demo_state = 0
                self.demo_run = False 
                self.timer.destroy()

    def timerControl(self): # camera below the LCD screen on the front of the AMR
       
        if (self.demo_run  == True):
            
            # move to out
            if self.demo_state == 1:
                time.sleep(1)
                self.update_x_with_accel(-0.1)
                time.sleep(0.5)
                self.demo_state  = self.demo_state  + 1

            # stop
            elif self.demo_state  == 2:                
                self.update_x_with_accel(0.0)
                time.sleep(0.1)
                self.update_x_with_accel(0.0)
                self.demo_state  = self.demo_state  + 1

            # move to side
            elif self.demo_state == 3:
                side_dir = random.choices([-1,1], weights=(10, 10), k=1)
                side_dir = side_dir[0]
                self.update_y_with_accel(0.1)
                time.sleep(0.05)
                self.demo_state  = self.demo_state  + 1

            # stop
            elif self.demo_state  == 4:
                self.update_y_with_accel(0.0)
                time.sleep(0.1)
                self.update_y_with_accel(0.0)
                self.demo_state  = self.demo_state  + 1

            # spin
            elif self.demo_state  == 5:
                self.turn_time = random.randint(4,8)
                self.turn_speed = random.choices([-0.5,-0.3,0.3,0.5], k=1)
                self.turn_speed = self.turn_speed[0]
                self.update_yaw_with_accel(self.turn_speed * (-1))
                time.sleep(self.turn_time)
                self.demo_state  = self.demo_state  + 1

            # spin back
            elif self.demo_state  == 6:
                self.update_yaw_with_accel(self.turn_speed)
                time.sleep(self.turn_time)
                self.demo_state  = self.demo_state  + 1

            # change rostopic status to dock
            elif self.demo_state  == 7:
                self.update_yaw_with_accel(0)
                time.sleep(3)
                # return to dock      
                self.state = "follow"
                msg =String()
                msg.data = "follow"
                self.state_pub.publish( msg)      
                self.demo_run  = False
            elif self.demo_state  == 0:
                self.update_yaw_with_accel(0)
                
    def timerControlOld(self): # Camera on the side of the robot
       
        if (self.demo_run  == True):
            
            # move to out
            if self.demo_state == 1:
                time.sleep(1)
                self.update_y_with_accel(-0.1)
                time.sleep(2.9)
                self.demo_state  = self.demo_state  + 1

            # stop
            elif self.demo_state  == 2:                
                self.update_y_with_accel(0.0)
                self.update_y_with_accel(0.0)
                self.demo_state  = self.demo_state  + 1

            # move to side
            elif self.demo_state == 3:
                side_dir = random.choices([-1,1], weights=(10, 20), k=1)
                side_dir = side_dir[0]
                self.update_x_with_accel(0.07 * side_dir)
                time.sleep(0.1)
                self.demo_state  = self.demo_state  + 1

            # stop
            elif self.demo_state  == 4:
                self.update_x_with_accel(0.0)
                time.sleep(1)
                self.update_x_with_accel(0.0)
                self.demo_state  = self.demo_state  + 1

            # spin
            elif self.demo_state  == 5:
                self.turn_time = random.randint(4,8)
                self.turn_speed = random.choices([-0.3,-0.2,0.2,0.3], k=1)
                self.turn_speed = self.turn_speed[0]
                self.update_yaw_with_accel(self.turn_speed * (-1))
                time.sleep(self.turn_time)
                self.demo_state  = self.demo_state  + 1

            # spin back
            elif self.demo_state  == 6:
                self.update_yaw_with_accel(self.turn_speed)
                time.sleep(self.turn_time)
                self.demo_state  = self.demo_state  + 1

            # change rostopic status to dock
            elif self.demo_state  == 7:
                self.update_yaw_with_accel(0)
                time.sleep(3)
                # return to dock      
                self.state = "follow"
                msg =String()
                msg.data = "follow"
                self.state_pub.publish( msg)      
                self.demo_run  = False
            elif self.demo_state  == 0:
                self.update_yaw_with_accel(0)
        

       
        

    def update_vel(self,x,y,yaw):

        vel_msg = Twist()
        
        vel_msg.linear.x = float(x)
        vel_msg.linear.y = float(y) 
        vel_msg.linear.z = 0.0
        vel_msg.angular.x = 0.0
        vel_msg.angular.y = 0.0
        vel_msg.angular.z = float(yaw)

        self.vel_publisher.publish(vel_msg)

    def update_y_with_accel(self,y):
        if(self.y_speed < y ):
            for i in np.arange(self.y_speed, y, 0.01):
                self.update_vel(0.0,i,0.0)
                time.sleep(0.15)

        elif(self.y_speed > y ):
            for i in np.arange(self.y_speed, y, -0.01):
                self.update_vel(0.0,i,0.0)
                time.sleep(0.15)

        self.update_vel(0.0,y,0.0)
        self.y_speed = y

    def update_x_with_accel(self,x):
        if(self.x_speed < x ):
            for i in np.arange(self.x_speed, x, 0.01):
                self.update_vel(i,0.0,0.0)
                time.sleep(0.2)

        elif(self.x_speed > x ):
            for i in np.arange(self.x_speed, x, -0.01):
                self.update_vel(i,0.0,0.0)
                time.sleep(0.2)

        self.update_vel(x,0.0,0.0)
        self.x_speed = x

    def update_yaw_with_accel(self,yaw):
        if(self.yaw_speed < yaw ):
            for i in np.arange(self.yaw_speed, yaw, 0.01):
                self.update_vel(0.0,0.0,i)
                time.sleep(0.2)

        elif(self.yaw_speed > yaw ):
            for i in np.arange(self.yaw_speed, yaw, -0.01):
                self.update_vel(0.0,0.0,i)
                time.sleep(0.2)

        self.update_vel(0.0,0.0,yaw)
        self.yaw_speed = yaw

def main(args=None):
    rclpy.init(args=args)
    node = DemoControl()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    except ExternalShutdownException:
        pass
    finally:
        node.stop()
        node.destroy_node()
        rclpy.try_shutdown()
    return

if __name__ == "__main__":
    #try:
    main()
    #except rclspy.ROSInterruptException:
    #    rclpy.loginfo("node terminated.")