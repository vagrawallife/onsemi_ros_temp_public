#include "ros2_onsemi_control/onsemi_comms.h"
// #include <ros/console.h>
#include <rclcpp/rclcpp.hpp>
#include <sstream>
#include <cstdlib>
#include <string>



void OnsemiComms::setup(const std::string &serial_device, int32_t baud_rate, int32_t timeout_ms)
{  
    serial_conn_.setPort(serial_device);
    serial_conn_.setBaudrate(baud_rate);
    serial::Timeout tt = serial::Timeout::simpleTimeout(timeout_ms);
    serial_conn_.setTimeout(tt); // This should be inline except setTimeout takes a reference and so needs a variabl

    try{
        serial_conn_.open();
    }
    catch (const std::exception& e){
        RCLCPP_WARN(rclcpp::get_logger("ControlOnsemiHardware"), "onsemi Comms NOT CONNECTED");
    }
    // serial_conn_.(serial_device, baud_rate, serial::Timeout::simpleTimeout(timeout_ms));

}


void OnsemiComms::sendEmptyMsg()
{
    std::string response = sendMsg("\r");
}

void OnsemiComms::readEncoderValues(int &val_1, int &val_2,int &val_3, int &val_4)
{
    // std::string response = sendMsg("e\r");

    // std::string delimiter = " ";
    // size_t del_pos = response.find(delimiter);
    // std::string token_1 = response.substr(0, del_pos);
    // std::string token_2 = response.substr(del_pos + delimiter.length());

    // val_1 = std::atoi(token_1.c_str());
    // val_2 = std::atoi(token_2.c_str());
}

void OnsemiComms::setMotorValues(double val_1, double val_2, double val_3, double val_4)
{
    std::stringstream ss;
    std::int8_t speed[4];
    char msg[40] {};
    char sign[4] {};


    //std::string ss;

    speed[0] = round(val_1*6); // convert from rpm to pwm
    speed[1] = round(val_2*6); // convert from rpm to pwm
    speed[2] = round(val_3*6); // convert from rpm to pwm
    speed[3] = round(val_4*6); // convert from rpm to pwm
    //speed[0] = round(val_1*(100/3000)); // convert from rpm to pwm
    //speed[1] = round(val_2*(100/3000)); // convert from rpm to pwm
    //speed[2] = round(val_3*(100/3000)); // convert from rpm to pwm
    //speed[3] = round(val_4*(100/3000)); // convert from rpm to pwm
    for (int i =0; i<4;i++){
        if (speed[i] < 0){
        sign[i] = '-';
        }else{
        sign[i] = '+';
        }
    }
    //RCLCPP_INFO( rclcpp::get_logger("OnsemiComms"), "Got command %.5f for %d!", val_1 , speed[0]);

    snprintf(msg,sizeof(msg),"%c%02d%c%02d%c%02d%c%02d\n",sign[0],abs(speed[0]),sign[1],abs(speed[1]),sign[2],abs(speed[2]),sign[3],abs(speed[3])); 
    RCLCPP_INFO( rclcpp::get_logger("OnsemiComms"), "Sending %s", msg);
    ss << msg << "\n";
    sendMsg(ss.str(), false);
}

void OnsemiComms::setPidValues(float k_p, float k_d, float k_i, float k_o)
{
    //std::stringstream ss;
    //ss << "u " << k_p << ":" << k_d << ":" << k_i << ":" << k_o << "\r";
    //sendMsg(ss.str());
}

std::string OnsemiComms::sendMsg(const std::string &msg_to_send, bool print_output)
{
    serial_conn_.write(msg_to_send);
    //std::string response = serial_conn_.readline();

    if (print_output)
    {
        //RCLCPP_INFO( rclcpp::get_logger("OnsemiComms"),"Sent: " << msg_to_send);
        // RCLCPP_INFO_STREAM(logger_,"Received: " << response);
    }

    //return response;
}