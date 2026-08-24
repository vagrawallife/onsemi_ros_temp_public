#include "ros2_onsemi_control/wheel.h"

#include <cmath>


Wheel::Wheel(const std::string &wheel_name, int counts_per_rev, int dir)
{
  setup(wheel_name, counts_per_rev, dir);
}


void Wheel::setup(const std::string &wheel_name, int counts_per_rev, int dir)
{
  name = wheel_name;
  rads_per_count = (2*M_PI)/counts_per_rev;
  direction = dir;
}

double Wheel::calcEncAngle()
{
  return enc * rads_per_count;
}