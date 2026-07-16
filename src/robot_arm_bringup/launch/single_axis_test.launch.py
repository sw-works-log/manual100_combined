from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction, RegisterEventHandler
from launch.event_handlers import OnProcessExit
from launch.substitutions import Command, FindExecutable, LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


JOINTS = {
    'gripper': 'gripper_joint',
    'gripper_joint': 'gripper_joint',
    'base': 'base_rotate_joint',
    'base_rotate_joint': 'base_rotate_joint',
}

CONTROLLER_CONFIGS = {
    'gripper_joint': 'single_axis_gripper_controller.yaml',
    'base_rotate_joint': 'single_axis_base_controller.yaml',
}


def launch_setup(context):
    axis = LaunchConfiguration('axis').perform(context)
    if axis not in JOINTS:
        raise RuntimeError(
            f"Invalid axis '{axis}'. Choose one of: {', '.join(JOINTS)}")

    joint = JOINTS[axis]
    description_share = get_package_share_directory('robot_arm_description')
    xacro_file = description_share + '/urdf/manual_total_robot.urdf.xacro'
    controller_file = description_share + '/config/' + CONTROLLER_CONFIGS[joint]
    xacro_command = [
        FindExecutable(name='xacro'), ' ', xacro_file,
        ' test_joint:=', joint,
        ' ifname:=', LaunchConfiguration('ifname'),
        ' shoulder_actuator_id:=', LaunchConfiguration('shoulder_actuator_id'),
        ' elbow_actuator_id:=', LaunchConfiguration('elbow_actuator_id'),
        ' wrist_actuator_id:=', LaunchConfiguration('wrist_actuator_id'),
        ' timeout:=', LaunchConfiguration('timeout'),
        ' dxl_port_name:=', LaunchConfiguration('dxl_port_name'),
        ' dxl_baud_rate:=', LaunchConfiguration('dxl_baud_rate'),
    ]
    robot_description = {
        'robot_description': ParameterValue(Command(xacro_command), value_type=str)}

    control = Node(
        package='controller_manager', executable='ros2_control_node',
        parameters=[controller_file, robot_description], output='screen')
    state_spawner = Node(
        package='controller_manager', executable='spawner',
        arguments=['joint_state_broadcaster', '-c', '/controller_manager'])
    position_spawner = Node(
        package='controller_manager', executable='spawner',
        arguments=['position_controller', '-c', '/controller_manager'])
    rmd_hold_spawner = Node(
        package='controller_manager', executable='spawner',
        arguments=['rmd_hold_controller', '-c', '/controller_manager'])

    return [
        Node(
            package='robot_state_publisher', executable='robot_state_publisher',
            parameters=[robot_description], output='screen'),
        control,
        state_spawner,
        RegisterEventHandler(OnProcessExit(
            target_action=state_spawner,
            on_exit=[rmd_hold_spawner, position_spawner])),
        Node(
            package='joy', executable='joy_node', name='joy_node',
            parameters=[{
                'dev': LaunchConfiguration('joy_dev'),
                'deadzone': 0.08,
            }]),
        Node(
            package='robot_arm_bringup', executable='safety_manager.py',
            name='safety_manager', output='screen', parameters=[{
                'control_toggle_button': LaunchConfiguration('control_toggle_button'),
                'manual_mode_button': LaunchConfiguration('manual_mode_button'),
                'emergency_stop_button': LaunchConfiguration('emergency_stop_button'),
            }]),
        Node(
            package='robot_arm_bringup',
            executable='single_axis_joystick_controller.py',
            name='single_axis_joystick_controller', output='screen',
            parameters=[{'joint_name': joint}]),
    ]


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument(
            'axis', default_value='gripper_joint',
            description='Dynamixel axis: gripper/gripper_joint or base/base_rotate_joint'),
        DeclareLaunchArgument('ifname', default_value='can_arm'),
        DeclareLaunchArgument('shoulder_actuator_id', default_value='4'),
        DeclareLaunchArgument('elbow_actuator_id', default_value='5'),
        DeclareLaunchArgument('wrist_actuator_id', default_value='6'),
        DeclareLaunchArgument('timeout', default_value='0'),
        DeclareLaunchArgument('dxl_port_name', default_value='/dev/ttyUSB0'),
        DeclareLaunchArgument('dxl_baud_rate', default_value='1000000'),
        DeclareLaunchArgument('joy_dev', default_value='/dev/input/js0'),
        DeclareLaunchArgument('control_toggle_button', default_value='9'),
        DeclareLaunchArgument('manual_mode_button', default_value='5'),
        DeclareLaunchArgument('emergency_stop_button', default_value='10'),
        OpaqueFunction(function=launch_setup),
    ])
