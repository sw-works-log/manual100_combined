#!/usr/bin/env python3
# 이 파일은 robot_description, ros2_control_node, controller spawner를 실행한다.
#
# Copyright 2025 ROBOTIS CO., LTD.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Author: Woojin Wie


from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import Command, FindExecutable, LaunchConfiguration, PathJoinSubstitution

from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    # Declare arguments
    declared_arguments = []

    declared_arguments.append(
        DeclareLaunchArgument(
            'prefix',
            default_value='""',
            description='Prefix of the joint names'
        )
    )

    declared_arguments.append(
        DeclareLaunchArgument(
            'description_file',
            default_value='dynamixel_system.urdf.xacro',
            description='URDF/XACRO description file with the robot.',
        )
    )

    declared_arguments.append(
        DeclareLaunchArgument(
            'port_name',
            default_value='/dev/ttyUSB0',
            description='Port name for the Dynamixel device.',
        )
    )

    declared_arguments.append(
        DeclareLaunchArgument(
            'baud_rate',
            default_value='1000000',
            description='Baudrate for the Dynamixel port.',
        )
    )

    description_file = LaunchConfiguration('description_file')
    prefix = LaunchConfiguration('prefix')
    port_name = LaunchConfiguration('port_name')
    baud_rate = LaunchConfiguration('baud_rate')

    robot_controllers = PathJoinSubstitution(
        [
            FindPackageShare('dynamixel_hardware_interface_example'),
            'config',
            'ros2_controllers.yaml',
        ]
    )

    robot_description_content = Command(
        [
            PathJoinSubstitution([FindExecutable(name='xacro')]),
            ' ',
            PathJoinSubstitution(
                [
                    FindPackageShare('dynamixel_hardware_interface_example'),
                    'config',
                    description_file,
                ]
            ),
            ' ',
            'prefix:=',
            prefix,
            ' ',
            'port_name:=',
            port_name,
            ' ',
            'baud_rate:=',
            baud_rate,
        ]
    )

    # 수정: Humble에서 xacro 출력이 YAML로 파싱되지 않도록 문자열 파라미터로 명시.
    robot_description = {
        'robot_description': ParameterValue(robot_description_content, value_type=str)
    }

    # 수정: controller_manager가 /robot_description 토픽을 기다리지 않도록 직접 전달.
    control_node = Node(
        package='controller_manager',
        executable='ros2_control_node',
        parameters=[robot_controllers, robot_description],
        output='both',
    )

    robot_controller_spawner = Node(
        package='controller_manager',
        executable='spawner',
        arguments=[
            'joint_state_broadcaster',
            '--controller-manager',
            '/controller_manager',
        ],
    )

    # 수정: 명령 토픽을 사용할 수 있도록 YAML에 정의된 position_controller를 실행.
    position_controller_spawner = Node(
        package='controller_manager',
        executable='spawner',
        arguments=[
            'position_controller',
            '--controller-manager',
            '/controller_manager',
        ],
    )

    robot_state_publisher_node = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        output='both',
        parameters=[robot_description],
    )

    nodes = [
        control_node,
        robot_controller_spawner,
        position_controller_spawner,
        robot_state_publisher_node,
    ]

    return LaunchDescription(declared_arguments + nodes)
