#ifndef onsemi_motor_node_ONSEMI_COMMS_H
#define onsemi_motor_node_ONSEMI_COMMS_H

#include <cstdio>

#include <chrono>
#include <cmath>
#include <cstddef>
#include <limits>
#include <memory>
#include <vector>
#include <cstring>
#include <sstream>
#include <cstdlib>
#include <string>

#include <serial/serial.h>
#include "rclcpp/rclcpp.hpp"
#include "std_msgs/msg/string.hpp"
//#include "std_msgs/msg/Int32MultiArray.hpp"
#include "std_msgs/msg/int32_multi_array.hpp"
#include "geometry_msgs/msg/twist.hpp"
#include "geometry_msgs/msg/transform_stamped.hpp"
#include "tf2/LinearMath/Quaternion.h"
#include "tf2_ros/transform_broadcaster.h"
#include "nav_msgs/msg/odometry.hpp"


#include "onsemi_control/wheel.hpp"
#include "onsemi_control/motor_driver.hpp"
#include "onsemi_control/config.h"
#include "onsemi_control/roboclaw.hpp"

class AmrControl : public rclcpp::Node
{

public:

  AmrControl(); 
  ~AmrControl();

private:

  typedef struct {
    double twist_x = 0.0 ;
    double twist_y = 0.0 ;
    double twist_rot = 0.0;
    bool new_twist = false;
    double vx = 0;
    double vy = 0;
    double vtheta = 0;
    double delta_x = 0;
    double delta_y = 0;
    double delta_theta = 0;
    double delta_wheel[4] = {0,0,0,0};
    double x = 0;
    double y = 0;
    double theta = 0;
  } Amr_info;

  void timer_callback();
  void twist_handler();
  void twist_callback(const geometry_msgs::msg::Twist::SharedPtr twist_msg);
  int smooth_acc_des(Wheel * m); // smooth acceleration or deseleration
  double get_fake_speed(Wheel * m);


  rclcpp::TimerBase::SharedPtr timer_, twist_timer_;
  rclcpp::Publisher<nav_msgs::msg::Odometry>::SharedPtr odom_pub_;
  rclcpp::Subscription<geometry_msgs::msg::Twist>::SharedPtr twist_sub_;
  rclcpp::Publisher<std_msgs::msg::String>::SharedPtr publisher_;
  rclcpp::Publisher<std_msgs::msg::Int32MultiArray>::SharedPtr wheel_publisher_;
  rclcpp::Time t_now, t_before;
  //rclcpp::Duration dt;

  std::unique_ptr<tf2_ros::TransformBroadcaster> tf_broadcaster_;

  Amr_info amr_ ; // used to store latest velosety inforamtion
  char motor_msg_[40] {};
  char sign_[4] {};
  //int speed_[4];
  double sp[4];
  int32_t wheel_en[4];
  int32_t wheel_en_pre[4];
  int32_t wheel_sp[4];
  size_t count_;
  bool in_progress_, smoothing_;
  Config cfg_;  
  MotorDriver motor_;
  
  //Wheel fl_wheel_;
  //Wheel fr_wheel_;
  //Wheel rl_wheel_;
  //Wheel rr_wheel_;
};

#endif // onsemi_motor_node_ONSEMI_COMMS_H
