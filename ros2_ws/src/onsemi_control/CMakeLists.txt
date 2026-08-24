cmake_minimum_required(VERSION 3.8)
project(onsemi_control)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

# find dependencies
set(THIS_PACKAGE_INCLUDE_DEPENDS
  hardware_interface
  pluginlib
  rclcpp
  rclcpp_lifecycle
  geometry_msgs
  nav_msgs
  controller_manager
  serial
  std_msgs
  tf2
  geometry_msgs
  tf2_ros
)
# find dependencies
find_package(ament_cmake REQUIRED)
foreach(Dependency IN ITEMS ${THIS_PACKAGE_INCLUDE_DEPENDS})
  find_package(${Dependency} REQUIRED)
endforeach()
# uncomment the following section in order to fill in
# further dependencies manually.
# find_package(<dependency> REQUIRED)


add_executable(onsemi_motor_node src/onsemi_motor_node.cpp src/motor_driver.cpp src/wheel.cpp src/roboclaw.cpp)
target_include_directories(onsemi_motor_node PUBLIC
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
  $<INSTALL_INTERFACE:include>)
target_compile_features(onsemi_motor_node PUBLIC c_std_99 cxx_std_17)  # Require C99 and C++17



# Add library dependencies
ament_target_dependencies( onsemi_motor_node PUBLIC ${THIS_PACKAGE_INCLUDE_DEPENDS}
)



install(
  DIRECTORY config launch
  DESTINATION share/${PROJECT_NAME}
)

install(TARGETS onsemi_motor_node
  DESTINATION lib/${PROJECT_NAME})

ament_export_dependencies(${THIS_PACKAGE_INCLUDE_DEPENDS})

ament_package()
