#!/usr/bin/env python3
"""Joystick position control for one joint selected by single_axis_test.launch.py."""

from typing import Optional

import rclpy
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
from sensor_msgs.msg import JointState, Joy
from std_msgs.msg import Bool, Float64MultiArray


class SingleAxisJoystickController(Node):
    JOINT_CONFIG = {
        'shoulder_lift_joint': {'axis': 3, 'rate': 0.1},
        'elbow_joint': {'axis': 4, 'rate': 0.1},
        'wrist_joint': {'axis': 1, 'rate': 0.1},
        'gripper_joint': {'positive_button': 1, 'negative_button': 3, 'rate': 0.15},
        'base_rotate_joint': {'positive_button': 2, 'negative_button': 0, 'rate': 0.15},
    }

    def __init__(self):
        super().__init__('single_axis_joystick_controller')
        self.declare_parameter('joint_name', 'shoulder_lift_joint')
        self.declare_parameter('command_topic', '/position_controller/commands')
        self.declare_parameter('publish_rate', 20.0)
        self.declare_parameter('axis_threshold', 0.5)
        self.declare_parameter('joy_timeout', 0.5)

        self.joint_name = str(self.get_parameter('joint_name').value)
        if self.joint_name not in self.JOINT_CONFIG:
            raise ValueError(f'Unsupported joint: {self.joint_name}')
        self.config = self.JOINT_CONFIG[self.joint_name]
        self.axis_threshold = float(self.get_parameter('axis_threshold').value)
        self.joy_timeout = float(self.get_parameter('joy_timeout').value)

        self.measured_position: Optional[float] = None
        self.target: Optional[float] = None
        self.joy: Optional[Joy] = None
        self.manual_enabled = False
        self.protective_stop = False
        self.last_joy_time = self.get_clock().now()
        self.last_time = self.get_clock().now()

        self.publisher = self.create_publisher(
            Float64MultiArray, self.get_parameter('command_topic').value, 10)
        self.create_subscription(JointState, '/joint_states', self.on_state, 10)
        self.create_subscription(Joy, '/joy', self.on_joy, 10)
        mode_qos = QoSProfile(
            depth=1, reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL)
        self.create_subscription(
            Bool, '/control/manual_enabled', self.on_manual_enabled, mode_qos)
        self.create_subscription(
            Bool, '/control/protective_stop', self.on_protective_stop, mode_qos)
        self.create_timer(
            1.0 / float(self.get_parameter('publish_rate').value), self.on_timer)

    def on_state(self, msg):
        if self.joint_name not in msg.name:
            return
        index = msg.name.index(self.joint_name)
        if index >= len(msg.position):
            return
        self.measured_position = float(msg.position[index])
        if self.target is None:
            self.target = self.measured_position
            self.get_logger().info(
                f'{self.joint_name} initialized at {self.target:.6f} rad.')

    def on_joy(self, msg):
        self.joy = msg
        self.last_joy_time = self.get_clock().now()

    def on_manual_enabled(self, msg):
        enabled = bool(msg.data)
        if enabled and not self.manual_enabled:
            self.target = self.measured_position
            self.get_logger().info('MANUAL mode enabled; target synchronized from encoder.')
        elif not enabled and self.manual_enabled:
            self.get_logger().info('MANUAL mode disabled; command publishing stopped.')
        self.manual_enabled = enabled

    def on_protective_stop(self, msg):
        if not msg.data:
            return
        self.protective_stop = True
        self.target = self.measured_position
        if self.target is not None:
            self.publisher.publish(Float64MultiArray(data=[self.target]))
        self.get_logger().fatal(
            'Protective E-stop received; joystick commands are permanently blocked.')

    def axis(self, index):
        if self.joy is None or index < 0 or index >= len(self.joy.axes):
            return 0.0
        value = self.joy.axes[index]
        if value > self.axis_threshold:
            return 1.0
        if value < -self.axis_threshold:
            return -1.0
        return 0.0

    def button(self, index):
        return (
            self.joy is not None and 0 <= index < len(self.joy.buttons)
            and self.joy.buttons[index] != 0)

    def direction(self):
        if 'axis' in self.config:
            return self.axis(self.config['axis'])
        return (
            float(self.button(self.config['positive_button']))
            - float(self.button(self.config['negative_button'])))

    def on_timer(self):
        now = self.get_clock().now()
        dt = min(max((now - self.last_time).nanoseconds * 1e-9, 0.0), 0.1)
        self.last_time = now
        if self.target is None or not self.manual_enabled or self.protective_stop:
            return

        joy_fresh = (now - self.last_joy_time).nanoseconds * 1e-9 <= self.joy_timeout
        direction = self.direction() if joy_fresh else 0.0
        self.target += direction * self.config['rate'] * dt
        self.publisher.publish(Float64MultiArray(data=[self.target]))


def main(args=None):
    rclpy.init(args=args)
    node = SingleAxisJoystickController()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
