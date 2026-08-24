
//#include "/opt/ros/humble/include/rclcpp/rclcpp/rclcpp.hpp"
#include <rclcpp/rclcpp.hpp>
#include <sstream>
#include <cstdlib>
#include <string>


#include <math.h>
#include <rcutils/logging_macros.h>
#include <stdint.h>

#include <algorithm>
#include <chrono>



#include "onsemi_control/wheel.hpp"
#include "onsemi_control/motor_driver.hpp"
#include "onsemi_control/roboclaw.hpp"

#include <iostream>

//#include "/home/onsemi/onsemi_ros/ros2_ws/src/roboclaw_serial/include/roboclaw_serial/device.hpp" // User for RoboClaw dual Motor Drive board if connected 
//#include "roboclaw_serial/device.hpp" // User for RoboClaw dual Motor Drive board if connected 




void MotorDriver::setup(const std::string &serial_device, int32_t baud_rate, int32_t timeout_ms)
{  
    serial_conn_.setPort(serial_device);
    serial_conn_.setBaudrate(baud_rate);
    serial::Timeout tt = serial::Timeout::simpleTimeout(timeout_ms);
    serial_conn_.setTimeout(tt); // This should be inline except setTimeout takes a reference and so needs a variable
    try{
        serial_conn_.open();
        RCLCPP_WARN(rclcpp::get_logger("Control"), "onsemi BLDC motor control CONNECTED ! %d ",this->motor_control_selection);
        if (this->motor_control_selection == roboclaw ){
            for (int i =0;i<5;i++){
                std::string line = serial_conn_.readline();
                RCLCPP_WARN( rclcpp::get_logger("MotorDriver"), "Setup %s %d", line.c_str(),i);            
            }
            readEncoderValues(this->wheel_en,true);
            for (int i =0; i<4;i++){
                RCLCPP_WARN( rclcpp::get_logger("MotorDriver"), "Encoder %d %d", i,this->wheel_en[i]);
            }
        }
        this->motors_connected = true;
        this->motor_comm_inprogress = false;
    } 
    catch (const std::exception& e){
        RCLCPP_WARN(rclcpp::get_logger("Control"), "onsemi BLDC motor control NOT CONNECTED ! ");
        this->motors_connected = false;
        this->motor_comm_inprogress = false;
    }
    for (int i =0; i<4;i++)
    {
      speedOld_[i] =-1; 
      speed_[i] = 0;
    }
    // serial_conn_.(serial_device, baud_rate, serial::Timeout::simpleTimeout(timeout_ms));

}


void MotorDriver::sendEmptyMsg()
{
    //std::string response = sendMsg("\r");
}

void MotorDriver::readEncoderValues(int32_t * val, bool reset)
{
    int t;

    robo_ctl01_->readSensorGroup();
    robo_ctl02_->readSensorGroup();

    wheel_en[1] = robo_ctl01_->getM1Encoder() * 1.0;
    wheel_en[0] = robo_ctl01_->getM2Encoder() * 1.0;
    val[0] = (wheel_en[0]); // / cfg.quad_pulses_per_revolution) * 2.0 * M_PI;
    val[1] = (wheel_en[1]); // / cfg.quad_pulses_per_revolution) * 2.0 * M_PI;
    wheel_en[3] = robo_ctl02_->getM1Encoder() * 1.0;
    wheel_en[2] = robo_ctl02_->getM2Encoder() * 1.0;
    val[2] = (wheel_en[2]); // / cfg.quad_pulses_per_revolution) * 2.0 * M_PI;
    val[3] = (wheel_en[3]); // / cfg.quad_pulses_per_revolution) * 2.0 * M_PI;


    //RCLCPP_WARN( rclcpp::get_logger("MotorDriver"), "encoder  %d %d %d %d", val[0],val[1],val[2],val[3]);

	
}        





double MotorDriver::smooth_acc_des( Wheel *m)
{
    if (m->new_speed > m->pre_speed){
      m->speed =  m->pre_speed + 5;   
      if (m->speed > m->new_speed) {
         m->speed = m->new_speed ;
      }
    }else{
      m->speed =  m->pre_speed - 5; 
      if (m->speed < m->new_speed) {
        m->speed = m->new_speed;   
      }
    }   
    //save speed setting for next time  
    m->pre_speed = m->speed;  
    return (m->speed); // convert from rpm to pwm            
}


void MotorDriver::roboSpeed(double x_velocity, double y_velocity, double yaw_velocity)
{   
    //if (RoboClaw::singleton() != nullptr) {

    if ((robo_ctl01_->singleton()!= nullptr) && (robo_ctl02_->singleton()!= nullptr)) {
        //RCUTILS_LOG_WARN(" Velpcity '%f' '%f' '%f' ", x_velocity, y_velocity, yaw_velocity);
        //x_velocity =   std::min(std::max(x_velocity, - cfg.max_linear_velocity), cfg.max_linear_velocity);
        //y_velocity =   std::min(std::max(y_velocity, - cfg.max_linear_velocity), cfg.max_linear_velocity);
        //yaw_velocity = std::min(std::max(yaw_velocity,- cfg.max_angular_velocity), cfg.max_angular_velocity);
        if ((fabs(x_velocity) < 0.01) && (fabs(y_velocity) < 0.01)  && (fabs(yaw_velocity) < 0.01)) { 
            //robo_ctl01_->stop();
            //robo_ctl02_->stop();
            fl_wheel_.new_speed = 0;
            fr_wheel_.new_speed = 0;
            rl_wheel_.new_speed = 0;
            rr_wheel_.new_speed = 0;
            //robo_ctl01_->doMixedSpeedAccelDist( 1000, 0, 0, 0, 0);
            //robo_ctl02_->doMixedSpeedAccelDist( 1000, 0, 0, 0, 0);
        } else {//if ((fabs(x_velocity) > 0.01) || (fabs(y_velocity) > 0.01)  || (fabs(yaw_velocity) > 0.01)){

            //RCUTILS_LOG_INFO("  speed %f %f %f", x_velocity, y_velocity,yaw_velocity );
            fl_wheel_.new_speed  = ((x_velocity - y_velocity - yaw_velocity * cfg.wheel_geometry ) / cfg.wheel_radius)*15;
            fr_wheel_.new_speed  = ((x_velocity + y_velocity + yaw_velocity * cfg.wheel_geometry ) / cfg.wheel_radius)*15;
            rl_wheel_.new_speed  = ((x_velocity + y_velocity - yaw_velocity * cfg.wheel_geometry ) / cfg.wheel_radius)*15;
            rr_wheel_.new_speed  = ((x_velocity - y_velocity + yaw_velocity * cfg.wheel_geometry ) / cfg.wheel_radius)*15;

        }

        //Clamp motor values
        fl_wheel_.new_speed = std::max(std::min(fl_wheel_.new_speed, 65.0), -65.0);
        fr_wheel_.new_speed = std::max(std::min(fr_wheel_.new_speed, 65.0), -65.0);
        rl_wheel_.new_speed = std::max(std::min(rl_wheel_.new_speed, 65.0), -65.0);
        rr_wheel_.new_speed = std::max(std::min(rr_wheel_.new_speed, 65.0), -65.0);


        speed_[3] = smooth_acc_des(& fl_wheel_);
        speed_[2] = smooth_acc_des(& fr_wheel_);
        speed_[1] = smooth_acc_des(& rl_wheel_);
        speed_[0] = smooth_acc_des(& rr_wheel_);
        //RCUTILS_LOG_INFO(" wheel RAW set'%f' '%f' '%f' '%f' ", fl_wheel_.speed, fr_wheel_.speed,rl_wheel_.speed,rr_wheel_.speed);
        //RCUTILS_LOG_INFO(" wheel set '%d' '%d' '%d' '%d' ", speed_[0], speed_[1], speed_[2],speed_[3]);
        try {
            robo_ctl01_->doMixedDuty( speed_[2], speed_[3]);
        }
        catch (...)
        {
            RCUTILS_LOG_INFO("Unknown exception caught RoboClaw01");
        }
        try {
            robo_ctl02_->doMixedDuty( speed_[0], speed_[1]);
        }
        catch (...)
        {
            RCUTILS_LOG_INFO("Unknown exception caught RoboClaw02");
        }
        
  }
}

void MotorDriver::roboSetup(const std::string &serial_device) {
    
    RoboClaws[0].device_name_ = "/dev/roboclaw_front";
    RoboClaws[1].device_name_ = "/dev/roboclaw_back";
    RoboClaws[0].device_port_ = 128;
    RoboClaws[1].device_port_ = 129;
    for (int i=0;i<2;i++)
    {
        RoboClaws[i].accel_quad_pulses_per_second_= 200;
        RoboClaws[i].m1_p_ = 5.00998;
        RoboClaws[i].m1_i_  = 0.9439;
        RoboClaws[i].m1_d_ =  0.0;
        RoboClaws[i].m1_qpps_ = 3000;
        RoboClaws[i].m1_max_current_ = 6.0;
        RoboClaws[i].m2_p_= 5.00998;
        RoboClaws[i].m2_i_= 0.9439;
        RoboClaws[i].m2_d_= 0.0;
        RoboClaws[i].m2_qpps_= 3000;
        RoboClaws[i].m2_max_current_= 6.0;
    }

    max_angular_velocity_= 0.03;
    max_linear_velocity_= 0.02;
    max_seconds_uncommanded_travel_= 1.25;

    publish_joint_states_= true;
    publish_odom_= true;
    quad_pulses_per_meter_= 1611;
    quad_pulses_per_revolution_= 537;
    vmin_= 1;
    vtime_= 2;
    wheel_radius_= 0.0480;
    wheel_separation_= 0.533;
    speed_to_pwm_= 10.00;
  
    RCUTILS_LOG_WARN("device_name 0: %s", RoboClaws[0].device_name_.c_str());
    RCUTILS_LOG_WARN("device_name 1: %s", RoboClaws[1].device_name_.c_str());
    RCUTILS_LOG_WARN("device_port: %d", RoboClaws[0].device_port_);
    RCUTILS_LOG_WARN("device_port: %d", RoboClaws[1].device_port_);
    
    RCUTILS_LOG_WARN("accel_quad_pulses_per_second: %d",RoboClaws[0].accel_quad_pulses_per_second_);   
    RCUTILS_LOG_WARN("m1_p: %f", RoboClaws[0].m1_p_);
    RCUTILS_LOG_WARN("m1_i: %f", RoboClaws[0].m1_i_);
    RCUTILS_LOG_WARN("m1_d: %f", RoboClaws[0].m1_d_);
    RCUTILS_LOG_WARN("m1_qpps: %d", RoboClaws[0].m1_qpps_);
    RCUTILS_LOG_WARN("m1_max_current: %f", RoboClaws[0].m1_max_current_);
    RCUTILS_LOG_WARN("m2_p: %f", RoboClaws[0].m2_p_);
    RCUTILS_LOG_WARN("m2_i: %f", RoboClaws[0].m2_i_);
    RCUTILS_LOG_WARN("m2_d: %f", RoboClaws[0].m2_d_);
    RCUTILS_LOG_WARN("m2_qpps: %d", RoboClaws[0].m2_qpps_);
    RCUTILS_LOG_WARN("m2_max_current: %f", RoboClaws[0].m2_max_current_);
    RCUTILS_LOG_WARN("max_angular_velocity: %f", max_angular_velocity_);
    RCUTILS_LOG_WARN("max_linear_velocity: %f", max_linear_velocity_);
    RCUTILS_LOG_WARN("max_seconds_uncommanded_travel: %f",  max_seconds_uncommanded_travel_);
    RCUTILS_LOG_WARN("publish_joint_states: %s",  publish_joint_states_ ? "True" : "False");
    RCUTILS_LOG_WARN("quad_pulses_per_meter: %d", quad_pulses_per_meter_);
    RCUTILS_LOG_WARN("quad_pulses_per_revolution: %d",  quad_pulses_per_revolution_);
    RCUTILS_LOG_WARN("vmin: %d", vmin_);
    RCUTILS_LOG_WARN("vtime: %d", vtime_);
    RCUTILS_LOG_WARN("wheel_radius: %f", wheel_radius_);
    RCUTILS_LOG_WARN("wheel_separation: %f", wheel_separation_);
    RCUTILS_LOG_WARN("speed_to_pwm: %f", speed_to_pwm_);
    
    RoboClaw::TPIDQ m1Pid = {RoboClaws[0].m1_p_, RoboClaws[0].m1_i_, RoboClaws[0].m1_d_, RoboClaws[0].m1_qpps_, RoboClaws[0].m1_max_current_};
    RoboClaw::TPIDQ m2Pid = {RoboClaws[0].m2_p_, RoboClaws[0].m2_i_, RoboClaws[0].m2_d_, RoboClaws[0].m2_qpps_, RoboClaws[0].m2_max_current_};
  

    std::string device;

    robo_ctl01_ = new RoboClaw(m1Pid, m2Pid, RoboClaws[0].m1_max_current_, RoboClaws[0].m2_max_current_, RoboClaws[0].device_name_.c_str(), RoboClaws[0].device_port_, vmin_, vtime_);
    robo_ctl02_ = new RoboClaw(m1Pid, m2Pid, RoboClaws[1].m1_max_current_, RoboClaws[1].m2_max_current_, RoboClaws[1].device_name_.c_str(), RoboClaws[1].device_port_, vmin_, vtime_);


 
    //RCUTILS_LOG_INFO("Main battery: %f", RoboClaw::singleton()->getMainBatteryLevel());
    RCUTILS_LOG_WARN("Main battery: %f", robo_ctl01_->getMainBatteryLevel());

  }
