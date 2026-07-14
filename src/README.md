# Source packages

## 의존 관계

```text
rmd_sdk ──────────────> rmd_hardware_interface ──┐
                                                 ├─> robot_arm_description
dynamixelSDK ─┬─> dynamixel_hardware_interface ──┤
              └─> dynamixel_interfaces           └─> robot_arm_bringup
```

- SDK 계층은 모터 통신 프로토콜을 담당합니다.
- hardware interface 계층은 SDK를 ros2_control의 state/command interface로 변환합니다.
- description은 실제 관절과 하드웨어 플러그인을 선언합니다.
- bringup은 controller와 운용 노드를 함께 실행합니다.

## 수정 위치 선택

| 변경하려는 내용 | 수정할 패키지 |
|---|---|
| CAN 프레임이나 RMD 명령 | `rmd_sdk` |
| RMD position/velocity/effort 연결 | `rmd_hardware_interface` |
| Dynamixel 통신 | `dynamixelSDK` |
| Dynamixel ros2_control 연결 | `dynamixel_hardware_interface` |
| 링크, 관절, 모터 ID 인자, controller 관절 | `robot_arm_description` |
| 게임패드, 모드 전환, 보호 정지, launch | `robot_arm_bringup` |

외부에서 가져온 SDK와 인터페이스를 수정할 때는 원본 프로젝트와 로컬 변경을 구분해 커밋 메시지에 남깁니다.

