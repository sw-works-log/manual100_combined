#!/usr/bin/env python3
"""게임패드 Joy 입력을 gripper_joint/base_yaw_joint position 명령으로 변환한다."""

import math

import rclpy
from rclpy.node import Node

from sensor_msgs.msg import Joy
from sensor_msgs.msg import JointState
from std_msgs.msg import Float64MultiArray


class GamepadTeleop(Node):
    """Integrate joystick axes into position commands for the two Dynamixel joints."""

    def __init__(self):
        super().__init__('gamepad_teleop')

        self.declare_parameter('joy_topic', '/joy')
        self.declare_parameter('joint_states_topic', '/joint_states')
        self.declare_parameter('command_topic', '/position_controller/commands')
        self.declare_parameter('publish_rate', 20.0)
        self.declare_parameter('enable_button', 9)  # PlayStation Options.
        self.declare_parameter('gripper_positive_button', 1)  # PlayStation Circle.
        self.declare_parameter('gripper_negative_button', 3)  # PlayStation Square.
        self.declare_parameter('base_yaw_positive_button', 2)  # PlayStation Triangle.
        self.declare_parameter('base_yaw_negative_button', 0)  # PlayStation Cross.
        self.declare_parameter('deadzone', 0.08)
        self.declare_parameter('gripper_rate', 0.35)   # rad/s at full stick.
        self.declare_parameter('base_yaw_rate', 0.45)  # rad/s at full stick.
        # 리밋: /joint_states가 180도를 0 rad 근처로 표현하므로 중심각 기준으로 제한한다.
        self.declare_parameter('gripper_min', math.radians(-170.0))  # MX 10도.
        self.declare_parameter('gripper_max', math.radians(169.0))   # MX 349도.
        self.declare_parameter('base_yaw_min', math.radians(-80.0))  # XH 100도.
        self.declare_parameter('base_yaw_max', math.radians(80.0))   # XH 260도.

        self.joy_topic = self.get_parameter('joy_topic').value
        self.joint_states_topic = self.get_parameter('joint_states_topic').value
        self.command_topic = self.get_parameter('command_topic').value
        publish_rate = float(self.get_parameter('publish_rate').value)

        self.enable_button = int(self.get_parameter('enable_button').value)
        self.gripper_positive_button = int(self.get_parameter('gripper_positive_button').value)
        self.gripper_negative_button = int(self.get_parameter('gripper_negative_button').value)
        self.base_yaw_positive_button = int(self.get_parameter('base_yaw_positive_button').value)
        self.base_yaw_negative_button = int(self.get_parameter('base_yaw_negative_button').value)
        self.deadzone = float(self.get_parameter('deadzone').value)
        self.gripper_rate = float(self.get_parameter('gripper_rate').value)
        self.base_yaw_rate = float(self.get_parameter('base_yaw_rate').value)
        self.gripper_min = float(self.get_parameter('gripper_min').value)
        self.gripper_max = float(self.get_parameter('gripper_max').value)
        self.base_yaw_min = float(self.get_parameter('base_yaw_min').value)
        self.base_yaw_max = float(self.get_parameter('base_yaw_max').value)

        self.last_joy = None
        self.movement_enabled = self.enable_button < 0
        self.previous_enable_button_pressed = False
        self.have_joint_state = False
        self.gripper_cmd = 0.0
        self.base_yaw_cmd = 0.0
        self.last_time = self.get_clock().now()

        self.command_pub = self.create_publisher(Float64MultiArray, self.command_topic, 10)
        self.create_subscription(Joy, self.joy_topic, self.joy_callback, 10)
        self.create_subscription(JointState, self.joint_states_topic, self.joint_state_callback, 10)

        timer_period = 1.0 / publish_rate if publish_rate > 0.0 else 0.05
        self.create_timer(timer_period, self.timer_callback)

        self.get_logger().info(
            '게임패드 제어 준비: Options 버튼으로 조작 모드를 켜고 끕니다. '
            'O/네모 버튼=gripper_joint, 세모/X 버튼=base_yaw_joint'
        )

    def joy_callback(self, msg):
        self.last_joy = msg
        self.update_enabled_state(msg)

    def joint_state_callback(self, msg):
        if self.have_joint_state:
            return

        state_by_name = dict(zip(msg.name, msg.position))
        if 'gripper_joint' not in state_by_name or 'base_yaw_joint' not in state_by_name:
            return

        self.gripper_cmd = self.clamp(
            state_by_name['gripper_joint'], self.gripper_min, self.gripper_max)
        self.base_yaw_cmd = self.clamp(
            state_by_name['base_yaw_joint'], self.base_yaw_min, self.base_yaw_max)
        self.have_joint_state = True
        self.get_logger().info(
            '초기 위치 동기화 완료: '
            f'gripper_joint={self.gripper_cmd:.3f}, base_yaw_joint={self.base_yaw_cmd:.3f}'
        )

    def timer_callback(self):
        now = self.get_clock().now()
        dt = (now - self.last_time).nanoseconds * 1e-9
        self.last_time = now

        if not self.have_joint_state:
            self.get_logger().warn(
                '아직 /joint_states에서 gripper_joint/base_yaw_joint를 받지 못했습니다.',
                throttle_duration_sec=5.0)
            return

        if self.last_joy is None:
            return

        if not self.is_enabled():
            return

        gripper_button_value = self.button_direction(
            self.last_joy,
            self.gripper_positive_button,
            self.gripper_negative_button,
            'gripper')
        base_yaw_button_value = self.button_direction(
            self.last_joy,
            self.base_yaw_positive_button,
            self.base_yaw_negative_button,
            'base_yaw')

        requested_gripper_cmd = self.gripper_cmd + gripper_button_value * self.gripper_rate * dt
        requested_base_yaw_cmd = self.base_yaw_cmd + base_yaw_button_value * self.base_yaw_rate * dt

        self.gripper_cmd = self.clamp(requested_gripper_cmd, self.gripper_min, self.gripper_max)
        self.base_yaw_cmd = self.clamp(requested_base_yaw_cmd, self.base_yaw_min, self.base_yaw_max)

        self.warn_if_limited(
            'gripper_joint', requested_gripper_cmd, self.gripper_cmd,
            self.gripper_min, self.gripper_max)
        self.warn_if_limited(
            'base_yaw_joint', requested_base_yaw_cmd, self.base_yaw_cmd,
            self.base_yaw_min, self.base_yaw_max)

        msg = Float64MultiArray()
        msg.data = [self.gripper_cmd, self.base_yaw_cmd]
        self.command_pub.publish(msg)

    def update_enabled_state(self, joy_msg):
        if self.enable_button < 0:
            self.movement_enabled = True
            self.previous_enable_button_pressed = False
            return
        if self.enable_button >= len(joy_msg.buttons):
            self.previous_enable_button_pressed = False
            self.get_logger().warn(
                f'enable_button index {self.enable_button}가 Joy buttons 범위를 벗어났습니다.',
                throttle_duration_sec=5.0)
            return

        pressed = joy_msg.buttons[self.enable_button] == 1
        if pressed and not self.previous_enable_button_pressed:
            self.movement_enabled = not self.movement_enabled
            state_text = 'ON' if self.movement_enabled else 'OFF'
            self.get_logger().info(f'게임패드 조작 모드 {state_text}')
        self.previous_enable_button_pressed = pressed

    def is_enabled(self):
        if self.enable_button < 0:
            return True
        return self.movement_enabled

    def button_direction(self, joy_msg, positive_button, negative_button, prefix):
        positive_pressed = self.button_pressed(joy_msg, positive_button, f'{prefix}_positive_button')
        negative_pressed = self.button_pressed(joy_msg, negative_button, f'{prefix}_negative_button')
        return float(positive_pressed) - float(negative_pressed)

    def button_pressed(self, joy_msg, button_index, parameter_name):
        if button_index < 0:
            return False
        if button_index >= len(joy_msg.buttons):
            self.get_logger().warn(
                f'{parameter_name} index {button_index}가 Joy buttons 범위를 벗어났습니다.',
                throttle_duration_sec=5.0)
            return False
        return joy_msg.buttons[button_index] == 1

    @staticmethod
    def clamp(value, lower, upper):
        return max(lower, min(upper, value))

    def warn_if_limited(self, joint_name, requested, limited, lower, upper):
        if math.isclose(requested, limited, rel_tol=0.0, abs_tol=1e-9):
            return

        limit_name = '하한' if requested < lower else '상한'
        self.get_logger().warn(
            f'{joint_name} {limit_name} 리밋 도달: '
            f'요청={requested:.3f} rad, 제한값={limited:.3f} rad. 더 이상 해당 방향으로 움직이지 않습니다.',
            throttle_duration_sec=2.0)


def main(args=None):
    rclpy.init(args=args)
    node = GamepadTeleop()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
