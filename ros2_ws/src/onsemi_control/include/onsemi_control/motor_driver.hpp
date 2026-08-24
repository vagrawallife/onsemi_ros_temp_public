#ifndef onsemi_control_ONSEMI_COMMS_H
#define onsemi_control_ONSEMI_COMMS_H

#include <serial/serial.h>
#include <cstring>
#include "onsemi_control/roboclaw.hpp"
#include "onsemi_control/config.h"
#include "rclcpp/rclcpp.hpp"


#define onsemi 1
#define roboclaw 2


class MotorDriver 
{


public:
  



  MotorDriver()
  {  }

  MotorDriver(const std::string &serial_device, int32_t baud_rate, int32_t timeout_ms)
      : serial_conn_(serial_device, baud_rate, serial::Timeout::simpleTimeout(timeout_ms))
  {  }

  void setup(const std::string &serial_device, int32_t baud_rate, int32_t timeout_ms);
  void sendEmptyMsg();
  void readEncoderValues(int32_t * val, bool reset);
  void setPidValues(float k_p, float k_d, float k_i, float k_o);
  bool connected() const { return serial_conn_.isOpen(); }
  int sendMsg(const std::string &msg_to_send, bool print_output = false);
  void niboSpeed(double x_velocity, double y_velocity, double yaw_velocity);
  double smooth_acc_des(Wheel * m); // smooth acceleration or deseleration
  void setMotorValues(double val_1, double val_2, double val_3, double val_4);
  // RoboClaw
  void roboSetup(const std::string &serial_device); 
  void roboSpeed(double x_velocity, double y_velocity, double yaw_velocity);
  int motor_control_selection ;

  Wheel fl_wheel_;
  Wheel fr_wheel_;
  Wheel rl_wheel_;
  Wheel rr_wheel_;
  int32_t wheel_en[4];

private:
  RoboClaw *robo_ctl01_;
  RoboClaw *robo_ctl02_;
  Config cfg;  


  typedef struct {
    uint32_t accel_quad_pulses_per_second_;
    std::string device_name_;
    uint8_t device_port_;
    float m1_p_;
    float m1_i_;
    float m1_d_;
    uint32_t m1_qpps_;
    float fr_speed;
    float m1_max_current_;
    float m2_p_;
    float m2_i_;
    float m2_d_;
    uint32_t m2_qpps_;
    float fl_speed;
    float m2_max_current_;
  } RoboClawBoard;

  char motor_msg_[40] {};
  uint8_t motor_read_[40] {};
  char sign_[4] {};
  int speed_[4];
  int speedOld_[4];

  Config cfg_;  
  RoboClawBoard RoboClaws[2]; 

  serial::Serial serial_conn_;  // use for onsemi motor control boards, NOT used for RoboClaws
  float max_angular_velocity_;  // Maximum allowed angular velocity.
  float max_linear_velocity_;   // Maximum allowed linear velocity.
  double max_seconds_uncommanded_travel_;

  bool publish_odom_;
  bool publish_joint_states_;
  bool motors_connected;
  bool motor_comm_inprogress;


  uint32_t quad_pulses_per_meter_;
  uint32_t quad_pulses_per_revolution_;
  uint8_t vmin_;
  uint8_t vtime_;
  double wheel_radius_;
  double wheel_separation_;
  double speed_to_pwm_;

};

#endif // onsemi_control_ONSEMI_COMMS_H
