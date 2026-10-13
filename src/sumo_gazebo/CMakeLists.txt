cmake_minimum_required(VERSION 3.8)
project(sumo_gazebo)

find_package(ament_cmake REQUIRED)

install(DIRECTORY launch worlds DESTINATION share/${PROJECT_NAME})
install(PROGRAMS scripts/referee.py scripts/cmd_vel_guard.py DESTINATION lib/${PROJECT_NAME})

ament_package()
