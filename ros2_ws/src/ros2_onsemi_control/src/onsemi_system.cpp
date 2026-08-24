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

#include "ros2_onsemi_control/onsemi_system.hpp"
#include "ros2_onsemi_control/tf_broadcaster.hpp"

#include <chrono>
#include <cmath>
#include <cstddef>
#include <limits>
#include <memory>
#include <vector>

#include "hardware_interface/types/hardware_interface_type_values.hpp"
#include "rclcpp/rclcpp.hpp"

namespace ros2_onsemi_control
{
hardware_interface::CallbackReturn ControlOnsemiHardware::on_init(
  const hardware_interface::HardwareInfo & info)
{
  if (
    hardware_interface::SystemInterface::on_init(info) !=
    hardware_interface::CallbackReturn::SUCCESS)
  {
    return hardware_interface::CallbackReturn::ERROR;
  }

  cfg_.front_left_wheel_name = info_.hardware_parameters["front_left_wheel_name"];
  cfg_.front_right_wheel_name = info_.hardware_parameters["front_right_wheel_name"];
  cfg_.rear_left_wheel_name = info_.hardware_parameters["rear_left_wheel_name"];
  cfg_.rear_right_wheel_name = info_.hardware_parameters["rear_right_wheel_name"];
  cfg_.loop_rate = std::stof(info_.hardware_parameters["loop_rate"]);
  cfg_.device = info_.hardware_parameters["device"];
  cfg_.baud_rate = std::stoi(info_.hardware_parameters["baud_rate"]);
  cfg_.timeout = std::stoi(info_.hardware_parameters["timeout"]);
  cfg_.enc_counts_per_rev = std::stoi(info_.hardware_parameters["enc_counts_per_rev"]);

  // Set up the wheels
  fl_wheel_.setup(cfg_.front_left_wheel_name, cfg_.enc_counts_per_rev,1);
  fr_wheel_.setup(cfg_.front_right_wheel_name, cfg_.enc_counts_per_rev,1);
  rl_wheel_.setup(cfg_.rear_left_wheel_name, cfg_.enc_counts_per_rev,1);
  rr_wheel_.setup(cfg_.rear_right_wheel_name, cfg_.enc_counts_per_rev,1);
  wheels_.push_back(fl_wheel_);
  wheels_.push_back(fr_wheel_);
  wheels_.push_back(rl_wheel_);
  wheels_.push_back(rr_wheel_);
  
  motor_.setup(cfg_.device, cfg_.baud_rate, cfg_.timeout);  
  RCLCPP_INFO(rclcpp::get_logger("ControlOnsemiHardware"), "Finished Configuration");


  // BEGIN: This part here is for exemplary purposes - Please do not copy to your production code
  hw_start_sec_ = std::stod(info_.hardware_parameters["example_param_hw_start_duration_sec"]);
  hw_stop_sec_ = std::stod(info_.hardware_parameters["example_param_hw_stop_duration_sec"]);
  // END: This part here is for exemplary purposes - Please do not copy to your production code
  // hw_positions_.resize(info_.joints.size(), std::numeric_limits<double>::quiet_NaN());
  // hw_velocities_.resize(info_.joints.size(), std::numeric_limits<double>::quiet_NaN());
  // hw_commands_.resize(info_.joints.size(), std::numeric_limits<double>::quiet_NaN());

  for (const hardware_interface::ComponentInfo & joint : info_.joints)
  {
    // onsemi System has exactly 4 states and one command interface on each joint
    if (joint.command_interfaces.size() != 1)
    {
      RCLCPP_FATAL(
        rclcpp::get_logger("ControlOnsemiHardware"),
        "Joint '%s' has %zu command interfaces found. 1 expected.", joint.name.c_str(),
        joint.command_interfaces.size());
      return hardware_interface::CallbackReturn::ERROR;
    }

    if (joint.command_interfaces[0].name != hardware_interface::HW_IF_VELOCITY)
    {
      RCLCPP_FATAL(
        rclcpp::get_logger("ControlOnsemiHardware"),
        "Joint '%s' have %s command interfaces found. '%s' expected.", joint.name.c_str(),
        joint.command_interfaces[0].name.c_str(), hardware_interface::HW_IF_VELOCITY);
      return hardware_interface::CallbackReturn::ERROR;
    }

    if (joint.state_interfaces.size() != 2)
    {
      RCLCPP_FATAL(
        rclcpp::get_logger("ControlOnsemiHardware"),
        "Joint '%s' has %zu state interface. 2 expected.", joint.name.c_str(),
        joint.state_interfaces.size());
      return hardware_interface::CallbackReturn::ERROR;
    }

    if (joint.state_interfaces[0].name != hardware_interface::HW_IF_POSITION)
    {
      RCLCPP_FATAL(
        rclcpp::get_logger("ControlOnsemiHardware"),
        "Joint '%s' have '%s' as first state interface. '%s' expected.", joint.name.c_str(),
        joint.state_interfaces[0].name.c_str(), hardware_interface::HW_IF_POSITION);
      return hardware_interface::CallbackReturn::ERROR;
    }

    if (joint.state_interfaces[1].name != hardware_interface::HW_IF_VELOCITY)
    {
      RCLCPP_FATAL(
        rclcpp::get_logger("ControlOnsemiHardware"),
        "Joint '%s' have '%s' as second state interface. '%s' expected.", joint.name.c_str(),
        joint.state_interfaces[1].name.c_str(), hardware_interface::HW_IF_VELOCITY);
      return hardware_interface::CallbackReturn::ERROR;
    }
  }
  //auto tf_node = std::make_shared<TfBroadcaster>("tf_broadcaster");
  //rclcpp::spin(tf_node);
  return hardware_interface::CallbackReturn::SUCCESS;
}

std::vector<hardware_interface::StateInterface> ControlOnsemiHardware::export_state_interfaces()
{
  std::vector<hardware_interface::StateInterface> state_interfaces;

  //We need to set up a position and a velocity interface for each wheel



  // for (auto i = 0u; i < wheels_.size(); i++)
  // {
  //   state_interfaces.emplace_back(hardware_interface::StateInterface(
  //     fl_wheel_.name, hardware_interface::HW_IF_VELOCITY, &wheels_[i].vel));
  //   state_interfaces.emplace_back(hardware_interface::StateInterface(
  //     fl_wheel_.name, hardware_interface::HW_IF_POSITION, &wheel_[i].pos));
  // }

  state_interfaces.emplace_back(hardware_interface::StateInterface(
    fl_wheel_.name, hardware_interface::HW_IF_VELOCITY, &fl_wheel_.vel));
  state_interfaces.emplace_back(hardware_interface::StateInterface(
    fl_wheel_.name, hardware_interface::HW_IF_POSITION, &fl_wheel_.pos));
  state_interfaces.emplace_back(hardware_interface::StateInterface(
    fr_wheel_.name, hardware_interface::HW_IF_VELOCITY, &fr_wheel_.vel));
  state_interfaces.emplace_back(hardware_interface::StateInterface(
    fr_wheel_.name, hardware_interface::HW_IF_POSITION, &fr_wheel_.pos));
  state_interfaces.emplace_back(hardware_interface::StateInterface(
    rl_wheel_.name, hardware_interface::HW_IF_VELOCITY, &rl_wheel_.vel));
  state_interfaces.emplace_back(hardware_interface::StateInterface(
    rl_wheel_.name, hardware_interface::HW_IF_POSITION, &rl_wheel_.pos));
  state_interfaces.emplace_back(hardware_interface::StateInterface(
    rr_wheel_.name, hardware_interface::HW_IF_VELOCITY, &rr_wheel_.vel));
  state_interfaces.emplace_back(hardware_interface::StateInterface(
    rr_wheel_.name, hardware_interface::HW_IF_POSITION, &rr_wheel_.pos));

  return state_interfaces;
}

std::vector<hardware_interface::CommandInterface> ControlOnsemiHardware::export_command_interfaces()
{
  std::vector<hardware_interface::CommandInterface> command_interfaces;
  // We need to set up a velocity command interface for each wheel
  command_interfaces.emplace_back(hardware_interface::CommandInterface(
    fl_wheel_.name, hardware_interface::HW_IF_VELOCITY, &fl_wheel_.cmd));
  command_interfaces.emplace_back(hardware_interface::CommandInterface(
    fr_wheel_.name, hardware_interface::HW_IF_VELOCITY, &fr_wheel_.cmd));
  command_interfaces.emplace_back(hardware_interface::CommandInterface(
    rl_wheel_.name, hardware_interface::HW_IF_VELOCITY, &rl_wheel_.cmd));
  command_interfaces.emplace_back(hardware_interface::CommandInterface(
    rr_wheel_.name, hardware_interface::HW_IF_VELOCITY, &rr_wheel_.cmd));

  return command_interfaces;
}

hardware_interface::CallbackReturn ControlOnsemiHardware::on_activate(
  const rclcpp_lifecycle::State & /*previous_state*/)
{

  RCLCPP_INFO(rclcpp::get_logger("ControlOnsemiHardware"), "Activating ...please wait...");

 
  RCLCPP_INFO(rclcpp::get_logger("ControlOnsemiHardware"), "Successfully activated!");

  return hardware_interface::CallbackReturn::SUCCESS;
}

hardware_interface::CallbackReturn ControlOnsemiHardware::on_deactivate(
  const rclcpp_lifecycle::State & /*previous_state*/)
{

  RCLCPP_INFO(rclcpp::get_logger("ControlOnsemiHardware"), "Deactivating ...please wait...");

 
  RCLCPP_INFO(rclcpp::get_logger("ControlOnsemiHardware"), "Successfully deactivated!");

  return hardware_interface::CallbackReturn::SUCCESS;
}

hardware_interface::return_type ControlOnsemiHardware::read(
  const rclcpp::Time & /*time*/, const rclcpp::Duration & period)
{

  auto new_time = std::chrono::system_clock::now();
  std::chrono::duration<double> diff = new_time - time_;
  double deltaSeconds = diff.count();
  double pos_prev;
  time_ = new_time;


  if (!motor_.connected())
  {
    return hardware_interface::return_type::ERROR;
  }

  motor_.readEncoderValues(fl_wheel_.enc, fr_wheel_.enc,rl_wheel_.enc, rr_wheel_.enc);

  pos_prev = fl_wheel_.pos;
  //fl_wheel_.pos = fl_wheel_.calcEncAngle();
  fl_wheel_.pos = (fl_wheel_.pos - pos_prev) / deltaSeconds;
  

  pos_prev = fr_wheel_.pos;
  //fr_wheel_.pos = fr_wheel_.calcEncAngle();
  fr_wheel_.pos = (fr_wheel_.pos - pos_prev) / deltaSeconds;

  pos_prev = rl_wheel_.pos;
  //rl_wheel_.pos = rl_wheel_.calcEncAngle();
  rl_wheel_.pos = (rl_wheel_.pos - pos_prev) / deltaSeconds;

  pos_prev = rr_wheel_.pos;
  //rr_wheel_.pos = rr_wheel_.calcEncAngle();
  rr_wheel_.pos = (rr_wheel_.pos - pos_prev) / deltaSeconds;

  if (fl_wheel_.pos != 0){
    RCLCPP_INFO( rclcpp::get_logger("ControlOnsemiHardware"),
        "Got position state %.5f and velocity state %.5f for '%s'!", fl_wheel_.pos, fl_wheel_.vel, info_.joints[0].name.c_str());
    // RCLCPP_INFO( rclcpp::get_logger("ControlOnsemiHardware"),
    //     "Got position state %.5f and velocity state %.5f for '%s'!", fr_wheel_.pos, fr_wheel_.vel, info_.joints[1].name.c_str());
    // RCLCPP_INFO( rclcpp::get_logger("ControlOnsemiHardware"),
    //     "Got position state %.5f and velocity state %.5f for '%s'!", rl_wheel_.pos, rl_wheel_.vel, info_.joints[2].name.c_str());
    // RCLCPP_INFO( rclcpp::get_logger("ControlOnsemiHardware"),
    //     "Got position state %.5f and velocity state %.5f for '%s'!", rr_wheel_.pos, rl_wheel_.vel, info_.joints[3].name.c_str());
  }

  return hardware_interface::return_type::OK;
}

hardware_interface::return_type ros2_onsemi_control ::ControlOnsemiHardware::write(
  const rclcpp::Time & /*time*/, const rclcpp::Duration & /*period*/)
{


  if (!motor_.connected())
  {
    return hardware_interface::return_type::ERROR;
  }

  int fl = fl_wheel_.cmd / fl_wheel_.rads_per_count / cfg_.loop_rate;
  int fr = fr_wheel_.cmd / fr_wheel_.rads_per_count / cfg_.loop_rate;
  int rl = rl_wheel_.cmd / rl_wheel_.rads_per_count / cfg_.loop_rate;
  int rr = rr_wheel_.cmd / rr_wheel_.rads_per_count / cfg_.loop_rate;

 
  //if (fl_wheel_.cmd != 0){
    //RCLCPP_INFO(
    //    rclcpp::get_logger("ControlOnsemiHardware"), "Got command %.5f for '%s'!", fl_wheel_.cmd , info_.joints[0].name.c_str());
    // RCLCPP_INFO(
    //     rclcpp::get_logger("ControlOnsemiHardware"), "Got command %.5f for '%s'!", fl_wheel_.cmd , info_.joints[1].name.c_str());
    // RCLCPP_INFO(
    //     rclcpp::get_logger("ControlOnsemiHardware"), "Got command %.5f for '%s'!", rl_wheel_.cmd , info_.joints[2].name.c_str());
    // RCLCPP_INFO(
    //     rclcpp::get_logger("ControlOnsemiHardware"), "Got command %.5f for '%s'!", rr_wheel_.cmd , info_.joints[3].name.c_str());
  //}

  // No feedback from wheel, dummy for now just use command values
  fl_wheel_.vel = fl_wheel_.cmd; 
  fr_wheel_.vel = fr_wheel_.cmd; 
  rl_wheel_.vel = rl_wheel_.cmd; 
  rr_wheel_.vel = rr_wheel_.cmd; 
  //motor_.setMotorValues(fl_wheel_.vel, fr_wheel_.vel, rl_wheel_.vel, rl_wheel_.vel);


  return hardware_interface::return_type::OK;
}

}  // namespace ros2_onsemi_control

#include "pluginlib/class_list_macros.hpp"
PLUGINLIB_EXPORT_CLASS(
  ros2_onsemi_control::ControlOnsemiHardware, hardware_interface::SystemInterface)
