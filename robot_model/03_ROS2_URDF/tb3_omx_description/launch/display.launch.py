#!/usr/bin/env python3
"""Show the industrial TurtleBot3 + OpenMANIPULATOR-X in RViz with joint sliders.

    ros2 launch tb3_omx_description display.launch.py
    ros2 launch tb3_omx_description display.launch.py gui:=false
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition, UnlessCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    share = get_package_share_directory('tb3_omx_description')
    with open(os.path.join(share, 'urdf', 'tb3_omx.urdf'), 'r') as f:
        robot_description = f.read()
    gui = LaunchConfiguration('gui')

    return LaunchDescription([
        DeclareLaunchArgument('gui', default_value='true', description='Joint slider GUI'),
        Node(package='robot_state_publisher', executable='robot_state_publisher',
             parameters=[{'robot_description': robot_description}], output='screen'),
        Node(package='joint_state_publisher_gui', executable='joint_state_publisher_gui',
             condition=IfCondition(gui)),
        Node(package='joint_state_publisher', executable='joint_state_publisher',
             condition=UnlessCondition(gui)),
        Node(package='rviz2', executable='rviz2', output='screen',
             arguments=['-d', os.path.join(share, 'rviz', 'display.rviz')]),
    ])
