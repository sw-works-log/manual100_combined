#!/usr/bin/env python3
# 이 파일은 joy_node와 gamepad_teleop 노드를 실행해 게임패드로 두 조인트를 제어한다.

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration

from launch_ros.actions import Node


def generate_launch_description():
    declared_arguments = [
        DeclareLaunchArgument(
            'dev',
            default_value='/dev/input/js0',
            description='Linux joystick device path.',
        ),
        DeclareLaunchArgument(
            'deadzone',
            default_value='0.08',
            description='Joystick deadzone.',
        ),
        DeclareLaunchArgument(
            'enable_button',
            default_value='9',
            description='Button index that toggles joint movement. Use -1 to always enable.',
        ),
        DeclareLaunchArgument(
            'gripper_positive_button',
            default_value='1',
            description='Button index that moves gripper_joint in the positive direction.',
        ),
        DeclareLaunchArgument(
            'gripper_negative_button',
            default_value='3',
            description='Button index that moves gripper_joint in the negative direction.',
        ),
        DeclareLaunchArgument(
            'base_yaw_positive_button',
            default_value='2',
            description='Button index that moves base_yaw_joint in the positive direction.',
        ),
        DeclareLaunchArgument(
            'base_yaw_negative_button',
            default_value='0',
            description='Button index that moves base_yaw_joint in the negative direction.',
        ),
    ]

    joy_node = Node(
        package='joy',
        executable='joy_node',
        name='joy_node',
        parameters=[{
            'dev': LaunchConfiguration('dev'),
            'deadzone': LaunchConfiguration('deadzone'),
        }],
        output='screen',
    )

    gamepad_teleop_node = Node(
        package='dynamixel_hardware_interface_example',
        executable='gamepad_teleop',
        name='gamepad_teleop',
        parameters=[{
            'enable_button': LaunchConfiguration('enable_button'),
            'gripper_positive_button': LaunchConfiguration('gripper_positive_button'),
            'gripper_negative_button': LaunchConfiguration('gripper_negative_button'),
            'base_yaw_positive_button': LaunchConfiguration('base_yaw_positive_button'),
            'base_yaw_negative_button': LaunchConfiguration('base_yaw_negative_button'),
            'deadzone': LaunchConfiguration('deadzone'),
        }],
        output='screen',
    )

    return LaunchDescription(declared_arguments + [joy_node, gamepad_teleop_node])
