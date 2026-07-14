# Manual Total Robot Workspace

RMD와 Dynamixel을 사용하는 로봇팔의 ROS 2 워크스페이스입니다. 현재는 운용자가 각 관절을 직접 움직이는 **Manual100** 모드를 우선 개발하고 있으며, 이후 로봇팔 반자동·자율 기능을 추가할 예정입니다.

## 현재 구현 상태

| 기능 | 상태 | 비고 |
|---|---|---|
| RMD shoulder/elbow 위치 제어 | 사용 가능 | CAN ID 기본값 4, 5 |
| RMD wrist 제어 | 비활성 | 하드웨어 설정 후 코드의 주석 해제 필요 |
| Dynamixel base/gripper 제어 | 비활성 | 현재 URDF의 ros2_control 블록이 주석 처리됨 |
| 게임패드 Manual100 | 사용 가능 | 활성 관절은 shoulder/elbow |
| 보호 정지 | 소프트웨어 구현 | 안전 인증된 하드웨어 E-stop을 대체하지 않음 |
| 로봇팔 반자동·자율 | 미구현 | 현재 placeholder 노드만 존재 |

## 패키지 구성

| 패키지 | 역할 |
|---|---|
| `rmd_sdk` | SocketCAN 기반 RMD 저수준 드라이버 |
| `rmd_hardware_interface` | RMD 드라이버를 ros2_control에 연결하는 플러그인 |
| `dynamixelSDK` | Dynamixel 저수준 통신 SDK |
| `dynamixel_hardware_interface` | Dynamixel ros2_control 플러그인 |
| `dynamixel_interfaces` | Dynamixel 전용 메시지와 서비스 |
| `robot_arm_description` | URDF/Xacro, 관절 정의, controller 설정 |
| `robot_arm_bringup` | 하드웨어 실행, 게임패드 제어, 모드 및 보호 정지 |

상세한 소스 구조는 [src/README.md](src/README.md)를 참고합니다.

## 개발 환경

- Ubuntu 22.04
- ROS 2 Humble
- `ros2_control`
- SocketCAN (`can0` 기본)
- Linux joystick (`/dev/input/js0` 기본)

## 처음 빌드하기

```bash
cd ~/manual_total_ws
source /opt/ros/humble/setup.bash
rosdep install --from-paths src --ignore-src -r -y
colcon build --symlink-install
source install/setup.bash
```

패키지명이나 디렉터리를 변경한 뒤에는 이전 CMake 경로가 남지 않도록 깨끗하게 다시 빌드합니다.

```bash
rm -rf build install log
source /opt/ros/humble/setup.bash
colcon build --symlink-install
source install/setup.bash
```

`dynamixel_hardware_interface`에는 현재 `COLCON_IGNORE`가 있습니다. 따라서 로컬 소스 대신 `/opt/ros/humble`에 설치된 1.5.0 패키지를 사용합니다. 로컬 소스를 수정하거나 프로젝트만으로 재현하려면 해당 파일을 제거한 뒤 클린 빌드해야 합니다.

## 실행

먼저 CAN 장치와 게임패드가 연결됐는지 확인합니다.

```bash
ip -details link show can0
ls -l /dev/input/js0
```

통합 Manual100 실행:

```bash
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 launch robot_arm_bringup robot_arm_bringup.launch.py
```

기본 RMD 설정은 shoulder CAN ID 4, elbow CAN ID 5, 최대 속도 5 deg/s입니다. 인자는 다음처럼 덮어쓸 수 있습니다.

```bash
ros2 launch robot_arm_bringup robot_arm_bringup.launch.py \
  ifname:=can0 shoulder_actuator_id:=4 elbow_actuator_id:=5 max_velocity:=5.0
```

RMD 하드웨어와 controller만 시험하는 별도 진입점은 다음과 같습니다.

```bash
ros2 launch robot_arm_bringup test_rmd_only.launch.py
```

## 관절명과 현재 controller 순서

표준 관절명은 다음과 같습니다.

1. `base_rotate_joint`
2. `shoulder_lift_joint`
3. `elbow_joint`
4. `wrist_joint`
5. `gripper_joint`

현재 활성 controller 배열은 `shoulder_lift_joint`, `elbow_joint` 두 개뿐입니다. 관절을 추가할 때 다음 세 곳의 **이름, 개수, 순서**를 반드시 같이 변경해야 합니다.

- `robot_arm_description/urdf/manual_total_robot.urdf.xacro`
- `robot_arm_description/config/manual_total_controllers.yaml`
- `robot_arm_bringup/scripts/manual_total_position_node.py`

자세한 활성화 절차는 [robot_arm_description README](src/robot_arm_description/README.md)에 정리되어 있습니다.

## 운용상 주의사항

- 처음에는 로봇팔을 기구적으로 고정하고 작업 반경을 비운 뒤 낮은 속도로 시험합니다.
- 실제 모터 CAN ID와 launch 인자가 일치하는지 먼저 확인합니다.
- `/joint_states`가 모두 들어오기 전에는 위치 명령을 보내지 않습니다.
- 소프트웨어 보호 정지는 안전 인증 회로가 아닙니다. 사람과 함께 운용할 때는 전원 차단형 하드웨어 E-stop과 기구 한계를 별도로 구성해야 합니다.
- 장비에서 `sudo`가 필요한 설정과 udev 규칙은 팀 내에서 동일하게 관리합니다.

## 문서 안내

- [소스 및 패키지 관계](src/README.md)
- [로봇 모델과 관절 활성화](src/robot_arm_description/README.md)
- [실행, 게임패드, 안전 상태](src/robot_arm_bringup/README.md)
- [RMD SDK](src/rmd_sdk/README.md)
- [RMD ros2_control 플러그인](src/rmd_hardware_interface/README.md)
