#ifndef onsemi_motor_ONSEMI_WHEEL_H
#define onsemi_motor_ONSEMI_WHEEL_H

#include <string>



class Wheel
{
    public:

        std::string name = "";
        int direction;
        int enc = 0;
        double cmd = 0;
        double pos = 0;
        double vel = 0;
        double eff = 0;
        double velSetPt = 0;
        double rads_per_count = 0;
        double speed = 0;
        double new_speed = 0;
        double pre_speed = 0;
        Wheel() = default;
        Wheel(const std::string &wheel_name, int counts_per_rev, int dir);  
        void setup(const std::string &wheel_name, int counts_per_rev, int dir);
        double calcEncAngle();



};


#endif // onsemi_motor_ONSEMI_WHEEL_H