#ifndef onsemi_control_CONFIG_H
#define onsemi_control_CONFIG_H

#include <string>
#define onsemi 1
#define roboclaw 2
#define PI  3.14159265358979323846

struct Config
{
  std::string front_left_wheel_name = "front_left_wheel";
  std::string front_right_wheel_name = "front_right_wheel";
  std::string rear_left_wheel_name = "rear_left_wheel";
  std::string rear_right_wheel_name = "rear_right_wheel";
  float loop_rate = 30;
  std::string device = "/dev/onsemi_motor";
  int baud_rate = 115200;
  int timeout = 100;

  double wheel_geometry = (0.241+0.292);
  
  double rpm_to_pwm = (100.0 / 3000.0); // convert from rpm to pwm
  double max_linear_velocity = 0.03;
  double max_linear_x_velocity_onsemi = 0.4;
  double max_linear_y_velocity_onsemi = 0.4;
  double max_angular_velocity_onsemi= 0.45;
  double max_angular_velocity= 0.02;

  double wheel_radius = 0.127; // Need to change for the wheel 0.0480;
  // for RoboClaw
  double wheel_circumference = PI * wheel_radius *2;
  double quad_pulses_per_revolution = 537.6;  // encoder pulses per revolution
  double accel_quad_pulses_per_second = 500;
  double quad_pulses_per_meter = (quad_pulses_per_revolution * (1/(2*wheel_circumference)));
  double max_seconds_uncommanded_travel = 100;
  double speed_cor = 0.0015;
 
  int system_configuration = onsemi; // roboclaw or onsemi   //ThK config for MIC-711
};


#endif // onsemi_control_CONFIG_H
