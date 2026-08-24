import rclpy
from rclpy.node import Node
import time,serial
from std_msgs.msg import String
 
 
class MatrixDriver(Node):
    def __init__(self, port = "/dev/onsemi_matrix"):
        super().__init__("matrix_node")
        self.get_logger().info("Matrix Node ROS2")
        self.port = port
        self.change = ''
        self.serialport = self.serialSetup(port)
        self.msg = String()
        self.msg.data = 'teleop'
        self.charge_wait = 60  # this is 30sec (60*timerInterval)
        self.charge_time = 0
        self.state = ''
        self.currentBorder = ''
        self.currentContent = ''
        self.setContent("O")
        self.setBorder("X")
        self.company_name = "O"
 
 
    def serialSetup(self, port):
        while True:
            try:
                self.serialPort = serial.Serial(port=port, baudrate =9600, timeout = .2)
                self.get_logger().info("Serial port opened successfully")
                return True
            except serial.serialutil.SerialException:
                self.get_logger().info("Serial port not found")
                return False

    def timerControl(self):
        """
        Timer callback for ROS Timer
        """
        #self.get_logger().info("rgb timer tick")
        if self.state == "charge":
            self.charge_time += 1
            if (self.charge_time > self.charge_wait):
                self.charge_time = 0  
                self.state='demo'    

    def setBorder(self,change):
        self.currentBorder = change
        if self.serialport == True:
            self.serialPort.write(('BORDER:' + change +'\n').encode())
            self.get_logger().info(('BORDER:' + change +'\n').encode())
            time.sleep(0.2)
            while self.serialPort.in_waiting > 0:
                self.serialPort.readline()

    def setContent(self,change):
        self.currentContent = change
        if self.serialport == True:
            self.serialPort.write(('CONTENT:' + change +'\n').encode())
            self.get_logger().info(('CONTENT:' + change +'\n').encode())
            time.sleep(0.2)
            while self.serialPort.in_waiting > 0:
                self.serialPort.readline()
    def stop(self):
        if self.serialport == True:
            self.serialPort.reset_input_buffer()
            self.serialPort.reset_output_buffer()
            self.serialPort.close()
            #self.stop()
            #self.destroy_node()
        return
