#ifndef onsemi_control_CONFIG_H
#define onsemi_control_CONFIG_H

#include <string>


struct Config
{
  std::string front_left_wheel_name = "front_left_wheel";
  std::string front_right_wheel_name = "front_right_wheel";
  std::string rear_left_wheel_name = "rear_left_wheel";
  std::string rear_right_wheel_name = "rear_right_wheel";
  float loop_rate = 30;
  //std::string device = "/dev/onsemi_motor";
  std::string device = "/dev/onsemi_motor";
  int baud_rate = 115200;
  int timeout = 1000;
  int enc_counts_per_rev = 1920;
};


#endif // onsemi_control_CONFIG_H