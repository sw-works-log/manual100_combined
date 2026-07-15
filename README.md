# manual_total_ws

RMD와 Dynamixel을 사용하는 재난구조 로봇팔의 ROS 2 제어 워크스페이스.
현재는 운용자가 게임패드로 각 관절을 직접 움직이는 **Manual100** 모드를 우선 개발하고 있으며, 이후 반자동·자율 기능을 추가할 예정

ROS 2 Humble + ros2_control + SocketCAN 기반

## 하드웨어 구성

| 조인트 | 액추에이터 | 통신 | 현재 상태 | 비고 |
|---|---|---|---|---|
| base (`base_rotate_joint`) | Dynamixel | TTL | 비활성 | URDF의 ros2_control 블록 주석 처리 |
| shoulder (`shoulder_lift_joint`) | RMD | CAN | 사용 가능 | 기본 CAN ID 4 |
| elbow (`elbow_joint`) | RMD | CAN | 사용 가능 | 기본 CAN ID 5 |
| wrist (`wrist_joint`) | RMD | CAN | 비활성 | 하드웨어 설정 후 코드 주석 해제 필요 |
| gripper (`gripper_joint`) | Dynamixel | TTL | 비활성 | URDF의 ros2_control 블록 주석 처리 |

기본 CAN 인터페이스는 `can0`, 게임패드 장치는 `/dev/input/js0`
현재 활성 controller 배열에는 `shoulder_lift_joint`, `elbow_joint`만 포함되어 있음

## 패키지 구성

- `robot_arm_description` — URDF/Xacro, 관절 정의, ros2_control 및 controller 설정
- `robot_arm_bringup` — 하드웨어 실행, 게임패드 Manual100 제어, 모드 및 보호 정지
- `rmd_sdk` — SocketCAN 기반 RMD 저수준 드라이버
- `rmd_hardware_interface` — RMD 드라이버를 ros2_control에 연결하는 플러그인
- `dynamixelSDK` — Dynamixel 저수준 통신 SDK
- `dynamixel_hardware_interface` — Dynamixel ros2_control 플러그인
- `dynamixel_interfaces` — Dynamixel 전용 메시지와 서비스

상세한 소스 구조와 패키지 관계는 [src/README.md](src/README.md)를 참고

## 빌드

개발 환경은 Ubuntu 22.04 & ROS 2 Humble

```bash
cd ~/manual_total_ws
source /opt/ros/humble/setup.bash
rosdep install --from-paths src --ignore-src -r -y
colcon build --symlink-install
source install/setup.bash
```

패키지명이나 디렉터리를 변경한 뒤에는 이전 CMake 경로가 남지 않도록 클린 빌드

```bash
rm -rf build install log
source /opt/ros/humble/setup.bash
colcon build --symlink-install
source install/setup.bash
```

`dynamixel_hardware_interface`에는 현재 `COLCON_IGNORE`가 있어 로컬 소스 대신 `/opt/ros/humble`에 설치된 1.5.0 패키지를 사용. 
로컬 소스를 수정하거나 이 저장소만으로 재현하려면 해당 파일을 제거한 뒤 클린 빌드

## 실행

### 1) 장치 연결 확인

```bash
ip -details link show can0
ls -l /dev/input/js0
```

실제 모터의 CAN ID와 launch 인자가 일치하는지 확인하고, 처음에는 로봇팔을 기구적으로 고정한 상태에서 낮은 속도로 시험

### 2) Manual100 통합 실행

```bash
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 launch robot_arm_bringup robot_arm_bringup.launch.py
```

기본 설정은 shoulder CAN ID 4, elbow CAN ID 5, 최대 속도 5 deg/s

```bash
ros2 launch robot_arm_bringup robot_arm_bringup.launch.py \
  ifname:=can0 shoulder_actuator_id:=4 elbow_actuator_id:=5 max_velocity:=5.0
```

### 3) RMD 하드웨어 단독 시험

```bash
ros2 launch robot_arm_bringup test_rmd_only.launch.py
```

### 4) 비활성 관절 추가

관절을 활성화할 때는 아래 세 파일의 관절 **이름, 개수, 순서**를 함께 변경

- `robot_arm_description/urdf/manual_total_robot.urdf.xacro`
- `robot_arm_description/config/manual_total_controllers.yaml`
- `robot_arm_bringup/scripts/manual_total_position_node.py`

구체적인 활성화 절차는 [robot_arm_description README](src/robot_arm_description/README.md)에 정리되어 있음

## 진행 상황

- [x] RMD shoulder/elbow 위치 제어
- [x] 게임패드 기반 Manual100 제어
- [x] 소프트웨어 보호 정지 로직
- [ ] RMD wrist 하드웨어 활성화
- [ ] Dynamixel base/gripper 활성화
- [ ] 로봇팔 반자동 기능
- [ ] 로봇팔 자율 기능

## 안전 주의사항

- 작업 반경을 비우고 로봇팔을 기구적으로 고정한 뒤 낮은 속도에서 처음 시험
- `/joint_states`가 모두 들어오기 전에는 위치 명령을 보내지 않음
- 소프트웨어 보호 정지는 안전 인증 회로가 아니다. 사람과 함께 운용할 때는 전원 차단형 하드웨어 E-stop과 기구 한계를 별도로 구성해야 함
- 장비에서 `sudo`가 필요한 설정과 udev 규칙은 팀 내에서 동일하게 관리함

## 참고

- [소스 및 패키지 관계](src/README.md)
- [로봇 모델과 관절 활성화](src/robot_arm_description/README.md)
- [실행, 게임패드, 안전 상태](src/robot_arm_bringup/README.md)
- [RMD SDK](src/rmd_sdk/README.md)
- [RMD ros2_control 플러그인](src/rmd_hardware_interface/README.md)
