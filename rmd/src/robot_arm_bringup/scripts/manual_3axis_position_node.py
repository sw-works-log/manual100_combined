#!/usr/bin/env python3

import math
from typing import Dict, List, Optional

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState, Joy
from std_msgs.msg import Float64MultiArray


class Manual3AxisPositionNode(Node):
    def __init__(self) -> None:
        super().__init__('manual_3axis_position_node')

        self.declare_parameter('joints', ['shoulder_joint', 'elbow_joint'])
        self.declare_parameter('command_topic', '/position_controller/commands')
        self.declare_parameter('publish_rate', 50.0)
        self.declare_parameter('target_step_per_second', [0.25, 0.25])
        self.declare_parameter('lower_limits', [-math.pi, -math.pi])
        self.declare_parameter('upper_limits', [math.pi, math.pi])
        self.declare_parameter('mode_toggle_button', 9)
        self.declare_parameter('dpad_x_axis', 3)
        self.declare_parameter('dpad_y_axis', 4)
        self.declare_parameter('axis_threshold', 0.5)
        self.declare_parameter('joy_timeout', 0.5)

        self.joints = self._string_list_parameter('joints')
        self.command_topic = self.get_parameter('command_topic').value
        self.publish_rate = float(self.get_parameter('publish_rate').value)
        self.steps = self._float_list_parameter('target_step_per_second', len(self.joints))
        self.lower_limits = self._float_list_parameter('lower_limits', len(self.joints))
        self.upper_limits = self._float_list_parameter('upper_limits', len(self.joints))
        self.mode_toggle_button = int(self.get_parameter('mode_toggle_button').value)
        self.dpad_x_axis = int(self.get_parameter('dpad_x_axis').value)
        self.dpad_y_axis = int(self.get_parameter('dpad_y_axis').value)
        self.axis_threshold = float(self.get_parameter('axis_threshold').value)
        self.joy_timeout = float(self.get_parameter('joy_timeout').value)

        self.last_joy: Optional[Joy] = None
        self.last_joy_time = self.get_clock().now()
        self.control_enabled = False
        self.toggle_button_was_pressed = False
        self.target: Optional[List[float]] = None
        self.current_positions: Dict[str, float] = {}
        self.last_update_time = self.get_clock().now()
        self.last_command_log_time = self.get_clock().now()

        self.command_pub = self.create_publisher(Float64MultiArray, self.command_topic, 10)
        self.create_subscription(Joy, '/joy', self._on_joy, 10)
        self.create_subscription(JointState, '/joint_states', self._on_joint_states, 10)

        period = 1.0 / self.publish_rate
        self.create_timer(period, self._on_timer)

        self.get_logger().info(
            '2축 position 제어 준비 완료: OPTIONS=조작 모드 ON/OFF, '
            '오른쪽 스틱 상/하=엘보, 좌/우=숄더. 현재 조작 모드 OFF.'
        )

    def _string_list_parameter(self, name: str) -> List[str]:
        values = self.get_parameter(name).value
        if not isinstance(values, list) or not all(isinstance(value, str) for value in values):
            raise ValueError(f'{name} 파라미터는 문자열 리스트여야 합니다')
        return values

    def _float_list_parameter(self, name: str, expected_length: int) -> List[float]:
        values = self.get_parameter(name).value
        if not isinstance(values, list) or len(values) != expected_length:
            raise ValueError(f'{name} 파라미터는 숫자 {expected_length}개의 리스트여야 합니다')
        return [float(value) for value in values]

    def _on_joy(self, msg: Joy) -> None:
        self.last_joy = msg
        self.last_joy_time = self.get_clock().now()
        toggle_pressed = self._button_pressed(self.mode_toggle_button)
        if toggle_pressed and not self.toggle_button_was_pressed:
            self.control_enabled = not self.control_enabled
            state = 'ON' if self.control_enabled else 'OFF'
            self.get_logger().info(f'매니퓰레이터 조작 모드 {state}')
        self.toggle_button_was_pressed = toggle_pressed

    def _on_joint_states(self, msg: JointState) -> None:
        for name, position in zip(msg.name, msg.position):
            self.current_positions[name] = position
        if self.target is None and all(joint in self.current_positions for joint in self.joints):
            self.target = [self.current_positions[joint] for joint in self.joints]
            self._clamp_targets()
            self.get_logger().info('현재 joint state 기준으로 매뉴얼 목표 위치를 초기화했습니다.')

    def _on_timer(self) -> None:
        now = self.get_clock().now()
        dt = max((now - self.last_update_time).nanoseconds * 1e-9, 0.0)
        self.last_update_time = now

        if self.target is None:
            return

        direction = self._read_direction(now)
        for index, sign in enumerate(direction):
            self.target[index] += sign * self.steps[index] * dt
        self._clamp_targets()
        self.command_pub.publish(Float64MultiArray(data=self.target))
        if any(direction):
            since_log = (now - self.last_command_log_time).nanoseconds * 1e-9
            if since_log >= 0.5:
                self.get_logger().info(
                    f'오른쪽 스틱 입력={direction}, position 목표={self.target}'
                )
                self.last_command_log_time = now

    def _read_direction(self, now) -> List[float]:
        stopped = [0.0] * len(self.joints)
        if self.last_joy is None:
            return stopped
        if not self.control_enabled:
            return stopped
        if (now - self.last_joy_time).nanoseconds * 1e-9 > self.joy_timeout:
            return stopped

        shoulder = self._axis_sign(self.dpad_x_axis)
        elbow = self._axis_sign(self.dpad_y_axis)
        return [shoulder, elbow]

    def _button_pressed(self, index: int) -> bool:
        if self.last_joy is None or index < 0 or index >= len(self.last_joy.buttons):
            return False
        return self.last_joy.buttons[index] != 0

    def _axis_sign(self, index: int) -> float:
        if self.last_joy is None or index < 0 or index >= len(self.last_joy.axes):
            return 0.0
        value = self.last_joy.axes[index]
        if value > self.axis_threshold:
            return 1.0
        if value < -self.axis_threshold:
            return -1.0
        return 0.0

    def _clamp_targets(self) -> None:
        if self.target is None:
            return
        for index, value in enumerate(self.target):
            self.target[index] = min(max(value, self.lower_limits[index]), self.upper_limits[index])


def main() -> None:
    rclpy.init()
    node = Manual3AxisPositionNode()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
