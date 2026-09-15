# 회로 생성 (에이전트가 circuit.data 를 직접 만든다)

2026-09-15 부터 회로도 저장소에서 만든다. 게임 GUI 없이 `circuit.data` 를 생성해 파운드리에 넣고,
사용자는 게임에서 열어 확인한다.

## 근거

- 세이브 형식: 게임 개발자가 공개한 [save_monger](https://github.com/Stuffe/save_monger) (CC0, 2026-08-31 갱신,
  형식 버전 16 지원). `tools/tcsave/` 는 그 `common.nim` + `versions/v16.nim` + `state_to_binary` 의 파이썬 이식.
  파일 = 버전 바이트 16 + snappy 원시 블록. 이 PC 의 버전 16 세이브 115개 중 113개가 바이트 단위로 왕복 일치했다
  (나머지 2개는 읽을 때 채우는 기본 settings 차이뿐).
- 핀 위치: 허브 아키텍처 "RISC-V"(id 130)의 `RV32I_ALU`, 캠페인 Overture 레벨 정답 회로에서 넷을 추적해 확인.
  실행 파일의 Verilog 원형(`module TC_Add (cin, in0, in1, out, cout)` 등)으로 핀 이름을 붙였다. 표는 `tools/tcgen/pins.py`.
- 배선 규칙: 허브 회로 112개에서 선끼리 끝점 없이 겹치는 점이 7276개 → 교차는 연결이 아니다. 선은 끝점에서만
  (핀 또는 다른 선 몸통에) 연결된다.

## 도구

| 파일 | 역할 |
|---|---|
| `tools/tcsave/snappy.py` | 순수 파이썬 snappy (압축은 리터럴만) |
| `tools/tcsave/save16.py` | v16 읽기/쓰기, JSON |
| `tools/tc_dump.py` | 세이브 요약/JSON 출력 |
| `tools/tcgen/pins.py` | 부품 종류별 핀 상대 좌표, 몸통 상자, 확신도 |
| `tools/tcgen/design.py` | 넷리스트 → 한 열 배치 → 레인 배선 → 검증 → Save |
| `tools/tcgen/sim.py` | 넷리스트 시뮬레이터 (게임에 넣기 전 논리 검증) |
| `tools/gen_alu64.py` | 첫 부품 `RV64G/ALU64` 생성기 (시뮬레이션 400벡터 대조 포함) |

```bash
python tools/gen_alu64.py build/ALU64          # build/ALU64/circuit.data
python tools/tc_dump.py build/ALU64/circuit.data
```

설치: `%APPDATA%\Turing Complete\schematics\foundry\RV64G\<이름>\circuit.data` (게임을 끄고 복사).

## 배선 방식 (design.py)

부품을 한 열에 세로로 쌓고 부품마다 행 띠를 독점한다. 넷마다 오른쪽 레인 x, 위쪽 고속도로 y, 왼쪽 레인 x 를
하나씩 독점하고, 출력 핀 → 오른쪽 레인 → 고속도로 → 왼쪽 레인 → 싱크 핀 순서로 한 선을 긋는다.
드라이버가 여럿인 넷(스위치 버스)은 나머지 드라이버가 오른쪽 레인에 닿는다. 검증기는 (1) 다른 넷의 끝점 위를
지나지 않는지, (2) 다른 넷의 핀 위를 지나지 않는지, (3) 부품 몸통 위를 지나지 않는지 본다.
크기는 넷 수에 비례해 커진다(ALU64: 27부품 52선, 42×143칸). 상위 보드용 압축 배선은 나중 일.

## 아직 게임에서 확인 못 한 것

| 항목 | 추정 | 확인 방법 |
|---|---|---|
| 생성한 파운드리 부품이 로드되는가 (design 4×6 블록, cc 핀 settings) | 허브 부품과 같은 값 사용 | ALU64 를 파운드리에서 연다 |
| `add` 의 cout 핀 | (0,+2) | ALU64 는 안 씀 |
| `constant` 출력 핀 | (3,0) | 다음 부품 |
| `static_indexer` 입력 핀 | (-2,0) 또는 (-3,0) | 다음 부품 |
| 커스텀 부품 인스턴스의 핀 배치 규칙 | cc 핀 settings[0] = 변(0 오른쪽, 2 왼쪽), 순서는 위치/ui_order | 상위 보드 만들 때 |
| 시프트량이 폭 이상일 때 게임 시프터 동작 | 0 | ALU64 테스트에서 b ≥ 64 |
