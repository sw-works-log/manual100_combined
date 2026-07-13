#!/usr/bin/env python3
"""Operator mode selection and latched software E-stop for the robot arm."""

from controller_manager_msgs.srv import SetHardwareComponentState, SwitchController
from lifecycle_msgs.msg import State
import rclpy
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
from sensor_msgs.msg import Joy
from std_msgs.msg import Bool, String
from std_srvs.srv import SetBool


class SafetyManager(Node):
    OFF = 'OFF'
    SEMIAUTO = 'SEMIAUTO'
    MANUAL = 'MANUAL'
    ESTOP_LATCHED = 'ESTOP_LATCHED'

    def __init__(self):
        super().__init__('safety_manager')
        self.declare_parameter('control_toggle_button', 9)
        self.declare_parameter('manual_mode_button', 7)
        self.declare_parameter('emergency_stop_button', 10)
        self.declare_parameter('rmd_hardware_components', ['shoulder_rmd', 'elbow_rmd'])
        self.control_button = int(self.get_parameter('control_toggle_button').value)
        self.manual_button = int(self.get_parameter('manual_mode_button').value)
        self.estop_button = int(self.get_parameter('emergency_stop_button').value)
        self.rmd_components = list(self.get_parameter('rmd_hardware_components').value)

        self.mode = self.OFF
        self.last_buttons = []
        self.estop_controller_future = None
        self.estop_dxl_future = None
        self.rmd_stop_futures = []
        self.estop_trigger_time = None
        self.completion_reported = False

        latched_qos = QoSProfile(
            depth=1, reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL)
        self.mode_pub = self.create_publisher(String, '/control/mode', latched_qos)
        self.control_enabled_pub = self.create_publisher(Bool, '/control/enabled', latched_qos)
        self.manual_enabled_pub = self.create_publisher(Bool, '/control/manual_enabled', latched_qos)
        self.semiauto_enabled_pub = self.create_publisher(Bool, '/control/semiauto_enabled', latched_qos)
        self.estop_pub = self.create_publisher(Bool, '/emergency_stop', latched_qos)
        self.switch_controller_client = self.create_client(
            SwitchController, '/controller_manager/switch_controller')
        self.set_hardware_state_client = self.create_client(
            SetHardwareComponentState, '/controller_manager/set_hardware_component_state')
        self.dxl_torque_client = self.create_client(
            SetBool, '/dynamixel_hardware_interface/set_dxl_torque')
        self.create_subscription(Joy, '/joy', self.on_joy, 10)
        self.create_timer(0.05, self.on_timer)
        self.estop_pub.publish(Bool(data=False))
        self.publish_mode()

    def pressed(self, msg, index):
        return 0 <= index < len(msg.buttons) and msg.buttons[index] != 0

    def rising(self, msg, index):
        previous = 0 <= index < len(self.last_buttons) and self.last_buttons[index] != 0
        return self.pressed(msg, index) and not previous

    def on_joy(self, msg):
        if self.mode != self.ESTOP_LATCHED and self.rising(msg, self.estop_button):
            self.trigger_estop()
        elif self.mode != self.ESTOP_LATCHED and self.rising(msg, self.control_button):
            self.mode = self.SEMIAUTO if self.mode == self.OFF else self.OFF
            self.publish_mode()
        elif self.mode != self.ESTOP_LATCHED and self.mode != self.OFF and self.rising(msg, self.manual_button):
            self.mode = self.MANUAL if self.mode == self.SEMIAUTO else self.SEMIAUTO
            self.publish_mode()
        self.last_buttons = list(msg.buttons)

    def publish_mode(self):
        enabled = self.mode in (self.SEMIAUTO, self.MANUAL)
        self.mode_pub.publish(String(data=self.mode))
        self.control_enabled_pub.publish(Bool(data=enabled))
        self.manual_enabled_pub.publish(Bool(data=self.mode == self.MANUAL))
        self.semiauto_enabled_pub.publish(Bool(data=self.mode == self.SEMIAUTO))
        self.get_logger().info(f'Operator control mode: {self.mode}')

    def trigger_estop(self):
        self.mode = self.ESTOP_LATCHED
        self.estop_trigger_time = self.get_clock().now()
        self.publish_mode()
        self.estop_pub.publish(Bool(data=True))
        self.get_logger().fatal(
            'EMERGENCY STOP LATCHED: stopping controller and disabling DXL/RMD torque. '
            'Restart bringup to recover.')

    def on_timer(self):
        if self.mode != self.ESTOP_LATCHED:
            return
        if self.estop_controller_future is None and self.switch_controller_client.service_is_ready():
            request = SwitchController.Request()
            request.deactivate_controllers = ['position_controller']
            request.strictness = SwitchController.Request.BEST_EFFORT
            request.activate_asap = True
            request.timeout.sec = 1
            self.estop_controller_future = self.switch_controller_client.call_async(request)
        if self.estop_dxl_future is None and self.dxl_torque_client.service_is_ready():
            self.estop_dxl_future = self.dxl_torque_client.call_async(SetBool.Request(data=False))

        controller_done = self.estop_controller_future is not None and self.estop_controller_future.done()
        elapsed = (self.get_clock().now() - self.estop_trigger_time).nanoseconds * 1e-9
        if (not self.rmd_stop_futures and self.set_hardware_state_client.service_is_ready()
                and (controller_done or elapsed >= 1.0)):
            target = State(id=State.PRIMARY_STATE_UNCONFIGURED, label='unconfigured')
            for component in self.rmd_components:
                request = SetHardwareComponentState.Request(name=component, target_state=target)
                self.rmd_stop_futures.append(
                    (component, self.set_hardware_state_client.call_async(request)))

        if (self.rmd_stop_futures and not self.completion_reported
                and all(future.done() for _, future in self.rmd_stop_futures)):
            for component, future in self.rmd_stop_futures:
                result = future.result()
                if result is None or result.state.id != State.PRIMARY_STATE_UNCONFIGURED:
                    self.get_logger().error(f'Failed to shut down {component}.')
            self.completion_reported = True
            self.get_logger().fatal('Emergency shutdown requests completed; restart is required.')


def main(args=None):
    rclpy.init(args=args)
    node = SafetyManager()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
