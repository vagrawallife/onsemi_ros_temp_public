cmake_minimum_required(VERSION 3.16)
project(ros2_onsemi_control LANGUAGES CXX)

if(CMAKE_CXX_COMPILER_ID MATCHES "(GNU|Clang)")
  add_compile_options(-Wall -Wextra)
endif()

# find dependencies
set(THIS_PACKAGE_INCLUDE_DEPENDS
  hardware_interface
  pluginlib
  rclcpp
  rclcpp_lifecycle
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


## COMPILE
add_library(
  ros2_onsemi_control
  SHARED
  src/onsemi_system.cpp
  src/onsemi_comms.cpp
  src/wheel.cpp
)
target_compile_features(ros2_onsemi_control PUBLIC cxx_std_17)
target_include_directories(ros2_onsemi_control PUBLIC
$<BUILD_INTERFACE:${PROJECT_SOURCE_DIR}/include>
$<INSTALL_INTERFACE:include/ros2_onsemi_control>
)
ament_target_dependencies(
  ros2_onsemi_control PUBLIC
  ${THIS_PACKAGE_INCLUDE_DEPENDS}
)

#target_link_libraries(ros2_onsemi_control PUBLIC serial)


# Causes the visibility macros to use dllexport rather than dllimport,
# which is appropriate when building the dll but not consuming it.
target_compile_definitions(${PROJECT_NAME} PRIVATE "ROS2_onsemi_control_BUILDING_DLL")

# Export hardware plugins
pluginlib_export_plugin_description_file(hardware_interface ros2_onsemi_control.xml)

# INSTALL
install(
  DIRECTORY include/
  DESTINATION include/ros2_onsemi_control
)
install(
  DIRECTORY description/launch description/ros2_control description/urdf
  DESTINATION share/ros2_onsemi_control
)
install(
  DIRECTORY bringup/launch bringup/config
  DESTINATION share/ros2_onsemi_control
)
install(TARGETS ros2_onsemi_control
  EXPORT export_ros2_control_demo_example_2
  ARCHIVE DESTINATION lib
  LIBRARY DESTINATION lib
  RUNTIME DESTINATION bin
)

if(BUILD_TESTING)
  find_package(ament_cmake_pytest REQUIRED)

  ament_add_pytest_test(example_2_urdf_xacro test/test_urdf_xacro.py)
  ament_add_pytest_test(view_example_2_launch test/test_view_robot_launch.py)
endif()

## EXPORTS
ament_export_targets(export_ros2_control_demo_example_2 HAS_LIBRARY_TARGET)
ament_export_dependencies(${THIS_PACKAGE_INCLUDE_DEPENDS})
ament_package()
