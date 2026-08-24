

#include "onsemi_control/onsemi_motor_node.hpp"

using namespace std::chrono_literals;

using std::placeholders::_1;

AmrControl::AmrControl(): Node("onsemi_motor_node"), count_(0)
{
  RCLCPP_INFO(rclcpp::get_logger("Control"), "onsemi_motor_node");
  for(int i=0;i<4;i++){
          wheel_en_pre[i]=0;
          wheel_en[4] = 0;
  }
  motor_.motor_control_selection = cfg_.system_configuration;
  if (motor_.motor_control_selection== onsemi){
    motor_.setup(cfg_.device, cfg_.baud_rate, cfg_.timeout);  // for onsemi motor control  BLDC
  }else{
    motor_.roboSetup(cfg_.device);  // for  RoboClaw motor control  Brushed
  }
 
  auto qos = rclcpp::QoS( rclcpp::QoSInitialization( RMW_QOS_POLICY_HISTORY_KEEP_LAST, 10));
  qos.reliability(RMW_QOS_POLICY_RELIABILITY_RELIABLE);
  qos.durability(RMW_QOS_POLICY_DURABILITY_VOLATILE);
  qos.avoid_ros_namespace_conventions(false);

  this->t_before = this->get_clock()->now();
  in_progress_ = false;
  publisher_ = this->create_publisher<std_msgs::msg::String>("topic", 10);
  wheel_publisher_ = this->create_publisher<std_msgs::msg::Int32MultiArray>("wheel_encoders", 10);
  twist_sub_ = this->create_subscription<geometry_msgs::msg::Twist>("/cmd_vel_out", 1, std::bind(&AmrControl::twist_callback, this, _1));
  twist_timer_ = this->create_wall_timer( 100ms, std::bind(&AmrControl::twist_handler, this));
  odom_pub_ = this->create_publisher<nav_msgs::msg::Odometry>("odom", 50);
  tf_broadcaster_ = std::make_unique<tf2_ros::TransformBroadcaster>(*this);
  timer_ = this->create_wall_timer( 500ms, std::bind(&AmrControl::timer_callback, this));
}

AmrControl::~AmrControl(){}

void AmrControl::twist_handler()
{
    if(!in_progress_)
    {
      in_progress_ = true;
      motor_.roboSpeed ( amr_.twist_x, amr_.twist_y, amr_.twist_rot );
      amr_.new_twist = false;
      in_progress_ = false;
    }
}


void AmrControl::twist_callback(const geometry_msgs::msg::Twist::SharedPtr twist_msg)
{

    amr_.twist_x = (-1)*twist_msg->linear.x; // push forward on Joystick drives backward hence -
    amr_.twist_y = (-1)*twist_msg->linear.y; // push left on Joystick drives right hence -
    amr_.twist_rot = (-1)*twist_msg->angular.z; // turn left on Joystick turns right hence -
    //RCLCPP_WARN(rclcpp::get_logger("Control"), "controller received command");

    amr_.new_twist = true;
}

void AmrControl::timer_callback()
{
      //auto message = std_msgs::msg::String();
      //message.data = "Hello, world! " + std::to_string(count_++);
      //RCLCPP_INFO(this->get_logger(), "Publishing: '%s'", message.data.c_str());
      //publisher_->publish(message);
      auto wheel_message = std_msgs::msg::Int32MultiArray();
      // Define the layout of the array (e.g., a 1x4 matrix)
      wheel_message.layout.dim.resize(2);
      wheel_message.layout.dim[0].label = "rows";
      wheel_message.layout.dim[0].size = 1;
      wheel_message.layout.dim[0].stride = 1 * 4; // rows * columns
      wheel_message.layout.dim[1].label = "cols";
      wheel_message.layout.dim[1].size = 4;
      wheel_message.layout.dim[1].stride = 4; // columns

      this->t_now = this->get_clock()->now();
      
      //forwared kinematics to calcualte amr velicities
      motor_.readEncoderValues(&this->wheel_en[0],false);
        // Populate the data
      wheel_message.data.resize(4); // 1 rows * 4 columns = 6 elements
      wheel_message.data[0] = static_cast<int32_t>(this->wheel_en[0]);
      wheel_message.data[1] = static_cast<int32_t>(this->wheel_en[1]);
      wheel_message.data[2] = static_cast<int32_t>(this->wheel_en[2]);
      wheel_message.data[3] = static_cast<int32_t>(this->wheel_en[3]);
      wheel_publisher_->publish(wheel_message);

      //this->dt = this->t_now - this->t_before;
      //double seconds = this->dt.seconds();

      for(int i=0;i<4;i++){
        //sp[i] = wheel_message.data[i];

        double ticks_per_second = (wheel_en[i]-wheel_en_pre[i]) / 0.5; // we are reading every 500ms
        double revolutions_per_second = ticks_per_second / cfg_.quad_pulses_per_revolution;
        sp[i] = revolutions_per_second * cfg_.wheel_circumference;
        wheel_en_pre[i] = wheel_en[i];
        amr_.delta_wheel[i] = amr_.delta_wheel[i]  + sp[i];//PI * 2 * ((wheel_en[i]-wheel_en_pre[i]) / cfg_.quad_pulses_per_revolution);
      }

      // sp[0] = smooth_acc_des(& fl_wheel_);
      // sp[1] = smooth_acc_des(& fl_wheel_);
      // sp[2] = smooth_acc_des(& fl_wheel_);
      // sp[3] = smooth_acc_des(& fl_wheel_);


      //RCLCPP_INFO(this->get_logger(), " wheel  mecanum   '%f' '%f' '%f' '%f' ", sp[0],sp[1],sp[2],sp[3]);

      amr_.vx =          (sp[0] + sp[1] + sp[2] + sp[3]) * (cfg_.wheel_radius/4.0);
      amr_.vy =     ((-1)*sp[0] + sp[1] + sp[2] + (-1)*sp[3]) * (cfg_.wheel_radius/4.0);
      amr_.vtheta = ((-1)*sp[0] + sp[1] + (-1)* sp[2] + sp[3]) * (cfg_.wheel_radius) * (1.0/(4.0*cfg_.wheel_geometry));
      //calculate odometry
      amr_.delta_x = (amr_.vx * cos(amr_.theta) - amr_.vy * sin(amr_.theta)) * (0.2);
      amr_.delta_y = (amr_.vx * sin(amr_.theta) + amr_.vy * cos(amr_.theta)) * (0.2);
      amr_.delta_theta = amr_.vtheta * (-0.2);
      amr_.x += amr_.delta_x;
      amr_.y += amr_.delta_y;
      amr_.theta += amr_.delta_theta;
     

      // Read message content and assign it to
      // corresponding tf variables
      geometry_msgs::msg::TransformStamped t;
      t.header.stamp = this->t_now;
      t.header.frame_id = "odom";
      t.child_frame_id = "base_link";
      t.transform.translation.x = amr_.x;
      t.transform.translation.y = amr_.y;
      t.transform.translation.z = 0.0;
      tf2::Quaternion q;
      q.setRPY(0, 0, amr_.theta);
      t.transform.rotation.x = q.x();
      t.transform.rotation.y = q.y();
      t.transform.rotation.z = q.z();
      t.transform.rotation.w = q.w();
      tf_broadcaster_->sendTransform(t);

      //publish odometry
      nav_msgs::msg::Odometry odom;
      odom.header.stamp = this->t_now;
      odom.header.frame_id = "odom";
      odom.child_frame_id = "base_link";
      //set the position
      odom.pose.pose.position.x = amr_.x;
      odom.pose.pose.position.y = amr_.y;
      odom.pose.pose.position.z = 0.0;
      odom.pose.pose.orientation.x = q.x();
      odom.pose.pose.orientation.y = q.y();
      odom.pose.pose.orientation.z = q.z();
      odom.pose.pose.orientation.w = q.w();   
      //set the velocity
      odom.twist.twist.linear.x = amr_.vx;
      odom.twist.twist.linear.y = amr_.vy;
      odom.twist.twist.angular.z = amr_.vtheta;
      //publish the message
      odom_pub_->publish(odom);

#if 1
      t.header.stamp = this->t_now;
      t.header.frame_id = "base_link";
      t.child_frame_id = "front_left_wheel_link";
      t.transform.translation.x = -0.245;
      t.transform.translation.y = -0.3;
      t.transform.translation.z = 0.0762;
      t.transform.rotation.x = 0.0;
      t.transform.rotation.y = amr_.delta_wheel[0]; 
      t.transform.rotation.z = 0.0;
      t.transform.rotation.w = 1.0;
      tf_broadcaster_->sendTransform(t);

      t.header.stamp = this->t_now;
      t.child_frame_id = "front_right_wheel_link";
      t.transform.translation.y = 0.3;
      t.transform.rotation.y = amr_.delta_wheel[1]; 
      tf_broadcaster_->sendTransform(t);

      t.header.stamp = this->t_now;
      t.child_frame_id = "rear_left_wheel_link";
      t.transform.translation.x = 0.245;
      t.transform.translation.y = -0.3;
      t.transform.rotation.y = amr_.delta_wheel[2]; 
      tf_broadcaster_->sendTransform(t);

      t.header.stamp = this->t_now;
      t.child_frame_id = "rear_right_wheel_link";
      t.transform.translation.y = 0.3;
      t.transform.rotation.y = amr_.delta_wheel[3]; 
      tf_broadcaster_->sendTransform(t);
#endif
   
      this->t_before =  this->t_now;
}

double AmrControl::get_fake_speed(Wheel *m)
{
      // get velocity of each wheel in rads/s
      //speed not queried from driver, last class speed is just returned
      return ( m->speed * (1.0/19.2) * (1.0/60.0) * (2*M_PI) * 1.72); // pm to rad/s and gear ratio
}


int main(int argc, char * argv[])
{
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<AmrControl>());
  rclcpp::shutdown();
  return 0;
}
