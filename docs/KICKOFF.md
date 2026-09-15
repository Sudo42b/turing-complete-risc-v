# 킥오프 — Turing Complete 안에 RV64G 만들기

## 한 줄 요약

게임 Turing Complete 의 아키텍처 샌드박스에서 RISC-V `RV64G`(정수 I, 곱셈 M, 원자 A, 부동소수점 F/D, CSR, fence.i)를
전부 구현한다. 어셈블러 정의와 설계 문서는 이 저장소에서, 회로는 게임 안에서 만들고, 모듈·확장 단위로 허브에 올린다.

## 왜 되는가

- 게임 부품이 2~64비트 폭을 지원해 64비트 데이터패스가 된다. 덧셈·곱셈·나눗셈·시프트·비교·RAM·포트가 기본 부품이다.
- 게임 어셈블러가 비트 슬라이싱, 가상 피연산자, PC 상대 오프셋(`$start`), 단언문, 리틀 엔디언을 지원해 RISC-V 의
  쪼개진 즉시값(B/J형)을 그대로 정의할 수 있다.
- 레지스터 파일은 64비트 RAM 하나에 로드 포트 2개, 스토어 포트 1개를 붙여 만든다. 게임 캠페인(Symphony)도
  "Register File" 이라는 이름의 RAM 을 그렇게 쓴다.

## 지금 있는 것

| 산출물 | 위치 | 상태 |
|---|---|---|
| RV64G 어셈블러 정의 (기본 명령 225 + 의사 명령 52) | `isa/rv64g.isa`, 확장별 조각 `isa/parts/` | 생성 완료 (즉시값 크기 타입 반영, 2026-09-14), 게임 검증 전 |
| 명령 표와 생성기, 참조 인코더 | `tools/rv64g/`, `tools/gen_isa.py`, `tools/rv_encode.py` | 자체 테스트 통과 (손계산 벡터 35개, 의사 명령 52개 교차 검증) |
| 어셈블러 검증 프로그램과 기대 바이트 | `tests/encode_check.asm`, `tests/encode_check.expected.txt` | 68 워드 |
| 하드웨어 모듈 설계 문서 13개 + 통합 문서 | `components/*/README.md` | 핀·내부 구조·배선 순서·검증값 |
| 검증 항목표 | `docs/verification-checklist.md` | 어셈블러 11개, 부품 12개. 게임 자료로 미리 답한 항목은 0절 |

## 역할

- 에이전트: ISA·인코더·테스트 프로그램·모듈 문서·검증표 관리, 그리고 회로 생성. 세이브 형식은 개발자 공개
  라이브러리(save_monger)로 확인했고 `tools/tcgen` 이 `circuit.data` 를 만든다 (`docs/circuit-generation.md`).
- 사용자: 게임에서 생성 부품 확인·실행, 검증 결과 기록, 허브 업로드. 손 배선은 생성기가 못 하는 부분만.

## 첫 주에 할 일

1. 샌드박스에 아키텍처 `RV64G` 를 만들고 `isa/rv64g.isa` 를 넣는다. 오류가 나면 `isa/rv64g_no_experimental.isa`.
2. `tests/encode_check.asm` 을 어셈블해 `tests/encode_check.expected.txt` 와 대조한다. 검증표 A1~A10 을 채운다.
3. 8비트 소형 실험으로 RAM 포트 동작(B1~B7)을 확인한다. 이 결과가 레지스터 파일·LSU·클록 방식을 정한다.
4. `components/00-pc` 부터 `05-alu` 까지 순서대로 만든다. 각 모듈 README 의 검증값으로 단위 테스트한다.
5. 모듈이 완성될 때마다 파운드리 `RV64G/<이름>` 으로 저장하고 허브에 올린 뒤, 폴더에 캡처와 링크를 남긴다.

## 순서와 단계

I → 분기/점프 → 로드/스토어 → W형 → M → Zicsr/Zifencei → A → F → D → 통합. 단일 사이클로 시작하고,
RAM 읽기 지연이 확인되면 2상 클록으로 바꾼다. F/D 는 하위 모듈(Unpack, Round, AddSub, Mul, Div, Sqrt, FMA, Cmp, Cvt)로 쪼개 하나씩 올린다.

## 규칙

- 명령 표를 고치면 `python tools/selftest.py` 통과 후 `python tools/gen_isa.py` 로 ISA 를 다시 만든다. 손으로 `.isa` 를 고치지 않는다.
- 피연산자 이름은 한 글자만 쓴다(게임 어셈블러가 첫 글자만 보기 때문).
- 즉시값 피연산자에는 크기 타입을 붙인다(`%i:S12(immediate)`). 게임 어셈블러가 타입 없는 즉시값을 거부한다
  (실행 파일의 오류 문구로 확인). 타입은 `tools/rv64g/formats.py` 의 `TYPE_OF` 한 곳에서 정한다.
- 회로 바이너리(`circuit.data`)는 저장소에 넣지 않는다. 캠페인용 파운드리 부품(`Overture/*`, `Hint */*`)은 건드리지 않는다.
- 게임 세이브 폴더를 만질 때는 게임을 끄고 `%APPDATA%\Turing Complete\backup\` 에 먼저 복사한다.

## 참고

- RISC-V 명세: https://riscv.org/technical/specifications/
- 게임 어셈블러 문서: `<게임 폴더>/asset/manual/Assembly/Language creation/`
- 다음 세션 인계 문서: `.claude/handoffs/`
