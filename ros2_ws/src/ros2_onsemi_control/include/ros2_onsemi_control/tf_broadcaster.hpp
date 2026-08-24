// Copyright 2021 ros2_control Development Team
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

#ifndef ROS2_TF_ONSEMI__ONSEMI_SYSTEM_HPP_
#define ROS2_TF_ONSEMI__ONSEMI_SYSTEM_HPP_

#include <rclcpp/rclcpp.hpp>
#include "geometry_msgs/msg/transform_stamped.hpp"
#include "geometry_msgs/msg/twist.hpp"
#include "tf2/LinearMath/Quaternion.h"
#include "tf2_ros/transform_broadcaster.h"

class TfBroadcaster : public rclcpp::Node{

public:
  TfBroadcaster(const std::string & name);
  
private:
    // Declare a timer for the tf_broadcaster_
    rclcpp::TimerBase::SharedPtr transform_timer_;
    // Declare the transforms broadcaster
    std::unique_ptr<tf2_ros::TransformBroadcaster> tf_broadcaster_;
    // Subscription for cmdVel
    rclcpp::Subscription<geometry_msgs::msg::Twist>::SharedPtr cmd_vel_sub_;
    // Declare the transform to broadcast
    geometry_msgs::msg::TransformStamped transf_;

    void armCallback(const geometry_msgs::msg::Twist::SharedPtr msg);
    void tfTimer();
  
};

#endif  // ROS2_TF_ONSEMI__ONSEMI_SYSTEM_HPP_
