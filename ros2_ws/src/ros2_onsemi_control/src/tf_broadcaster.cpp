#include "ros2_onsemi_control/tf_broadcaster.hpp"

TfBroadcaster::TfBroadcaster(const std::string & name):
 : rclcpp::Node(name)
 {
    // Initialize the transforms broadcaster
    tf_broadcaster_ = std::make_unique<tf2_ros::TransformBroadcaster>(*this);
    // Define the "parent" frame
    transf_.header.frame_id = "odom";
    // Define the "child" frame
    transf_.child_frame_id = "base_link";
    // Initialize timer for publishing transform
    transform_timer_ = create_wall_timer(std::chrono::seconds(1), std::bind(&TfBroadcaster::tfTimer, this));
    // Create subscriber for cmdVel
    cmd_vel_sub_ = create_subscription<geometry_msgs::msg::Twist>(
      "/cmd_vel",10,std::bind(&TfBroadcaster::armCallback, this, std::placeholders::_1));
  }

void TfBroadcaster::armCallback(const geometry_msgs::msg::Twist::SharedPtr msg){
    transf_.transform.translation.x = msg->linear.x;
    transf_.transform.translation.y = msg->linear.y;
    tf2::Quaternion q;
    q.setRPY(0,0,msg->angular.z);
    transf_.transform.rotation.x = q.getX();
    transf_.transform.rotation.y = q.getY();
    transf_.transform.rotation.z = q.getZ();
    transf_.transform.rotation.w = q.getW();
}

void TfBroadcaster::tfTimer(){
    // All transforms must be correctly timestamped
    transf_.header.stamp = this->get_clock()->now();
    tf_broadcaster_->sendTransform(transf_);
}

int main(int argc, char const *argv[]){
  rclcpp::init(argc, argv);
  auto node = std::make_shared<TfBroadcaster>("tf_broadcaster");
  rclcpp::spin(node);
  return 0;
}