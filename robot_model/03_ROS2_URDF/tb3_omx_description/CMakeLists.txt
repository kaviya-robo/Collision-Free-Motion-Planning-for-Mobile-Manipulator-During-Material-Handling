cmake_minimum_required(VERSION 3.8)
project(tb3_omx_description)

find_package(ament_cmake REQUIRED)

install(
  DIRECTORY urdf meshes launch rviz
  DESTINATION share/${PROJECT_NAME}
)
install(
  PROGRAMS scripts/use_with_turtlebot3_manipulation.sh
  DESTINATION lib/${PROJECT_NAME}
)

ament_package()
