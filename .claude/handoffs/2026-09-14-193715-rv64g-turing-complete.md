# Handoff: Turing Complete 안에서 RV64G CPU 전부 구현하기

## Session Metadata
- Created: 2026-09-14 19:37:15
- Project: C:\Users\sw.lee\Desktop\turing-complete-korean-patch\turing-complete-risc-v (자체 git 저장소, origin = github.com/Sudo42b/turing-complete-risc-v, 아직 커밋 없음)
- Branch: main
- Session duration: 약 1시간 10분 (RV64G 조사 부분만. 세션 전체는 한국어 패치 릴리즈, CI 수정, 캠페인 정답 주입 포함)
- Continues from: None
- Supersedes: None

## Current State Summary

**2026-09-15 오후 (세션 4 계속) 갱신 — 회로 생성 가능해짐.** 사용자가 "허브 회로처럼 네가 만들 수 없느냐"고 물어
조사한 결과, 게임 개발자가 세이브 형식 라이브러리 save_monger(github.com/Stuffe/save_monger, CC0, v16 지원)를
공개하고 있었다. `tools/tcsave/` 에 파이썬으로 이식했고(순수 파이썬 snappy 포함) 이 PC 의 v16 세이브 113/115 가
바이트 단위로 왕복 일치한다. 허브 아키텍처 "RISC-V"(id 130, RV32I) 와 캠페인 정답 회로에서 넷을 추적해 부품 핀
좌표표(`tools/tcgen/pins.py`)를 만들었고, 선은 끝점에서만 연결된다(교차 7276개 관찰)는 것도 확인했다.
`tools/tcgen/design.py` 가 넷리스트를 한 열 배치 + 레인 배선으로 `circuit.data` 로 만들고 검증하며,
`tools/tcgen/sim.py` 로 게임에 넣기 전에 시뮬레이션한다. 첫 부품 `RV64G/ALU64`(`tools/gen_alu64.py`, 27부품 52선,
400벡터 일치)를 `%APPDATA%\Turing Complete\schematics\foundry\RV64G\ALU64\circuit.data` 에 설치했다.
게임에서는 아직 안 열어 봤다(검증표 D1~D5). 미확인: constant/static_indexer 핀, add cout, 커스텀 인스턴스 핀 배치 규칙.
한편 ISA 는 A1 첫 오류(`%o[20]` 단일 비트 슬라이스 → `[20:20]` 필요)를 고쳐 재생성해 두었고, 188행까지는 파서를 통과했다.
참고 도구: liquidhelium/verilog-target-turing-complete (Verilog→v6 세이브, yosys+ELK, 스크래치패드 vttc/ 에 빌드됨) 는
대안 경로로 남겨 둔다. 다음: 사용자가 D1~D5 를 확인 → 결과로 핀표 수정 → 00-pc, 03-imm-gen, 04-regfile 순서로 생성.

**2026-09-15 (세션 4) 갱신.** 사용자가 샌드박스에 아키텍처 `RV64G` 를 만들었다(`schematics\architecture\RV64G\`,
`settings.txt` 의 `setting_loaded_architecture = RV64G`). 게임 자료와 폴더 관찰로 확정한 것:
(1) 아키텍처 종류 레벨(The Sandbox, Maze …)은 세이브를 `schematics\architecture\<이름>\` 하나로 공유하고,
레벨별 상태는 `<이름>\<레벨>\` 아래에 둔다(`RV64G\sandbox\sandbox\sandbox.json`).
(2) 이 엔진에는 Program 부품이 없다(실행 파일 부품 id 에 `com_program` 없음). RAM(`com_ram`)이 프로그램 메모리이고,
RAM 의 메모리 내용은 `<이름>\<레벨>\<부품id>.bin` 에 저장된다. IDE 는 RAM 의 "프로그램 편집" 아이콘으로 연다.
(3) 게임은 ISA 를 폴더에서 찾지 않는다. 사용자가 RAM 의 "파일 불러오기"로 `spec.isa` 를 메모리 데이터로 넣었는데
무해하다(어셈블하면 덮어씀). RAM 크기는 256 으로 두었는데 검증 프로그램만 272바이트라 512 이상(권장 65536)이 필요하다.
(4) 에이전트가 `RV64G\spec.isa`, `RV64G\new_program.asm`, `RV64G\sandbox\sandbox\spec.isa` 등을 CRLF 로 심어
두었지만 게임이 읽는지는 미확인. 사용자가 폴더를 `Default\sandbox\` 로 옮겼던 것을 게임 종료 후 되돌렸다
(백업 `%APPDATA%\Turing Complete\backup\RV64G-20260915-105312`).
**다음 할 일:** RAM 의 "프로그램 편집" → IDE 의 `spec.isa` 탭에 `name = "RV64G"` 가 보이는지 확인 → 안 보이면
탭에서 전체 선택 후 `isa/rv64g.isa` 붙여넣기 → `tests/encode_check.asm` 어셈블 → 검증표 A1~A11. IDE 를 열면
게임이 `spec.isa`/`.asm` 을 실제로 쓰는 경로가 폴더에 드러나므로 그때 B12 를 확정한다.

**2026-09-14 (세션 3) 갱신.** 게임 실행 파일(`Turing Complete.exe`)의 어셈블러 오류 문구를 뽑아 보니 즉시값 피연산자에
크기 타입이 필수였다("Immediate operand must have size constraint, e.g. %a:U8(immediate)", 부호형 `S<n>` 존재).
이전 ISA 는 타입 없는 `%i(immediate)` 라 A1 에서 바로 실패했을 것이다. `tools/rv64g/formats.py` 에 `TYPE_OF`
(S12/U20/U6/U5/U12/U32/S33)를 넣어 ISA 를 재생성했고(1495줄, 타입이 대신하는 범위 단언문 42개 제거), `selftest.py` 에
타입 없는 즉시값 검사를 추가했다. 기대 바이트는 변하지 않았다. 게임 안 텍스트(한국어 패치 저장소의
`translation_dict.json` 원문)에서 B1/B2/B3/B4/B5 의 예상 답(RAM 하나에 포트 여러 개, Fast RAM 은 지연 없음, 메모리는
앞 단계 읽기·뒤 단계 쓰기, 바이트 주소, 폭별 포트)을 얻어 `docs/verification-checklist.md` 0절에 근거와 함께 적었다.
게임에서는 여전히 아무것도 확인하지 않았고, 커스텀 아키텍처 폴더(`schematics\architecture\RV64G`)도 아직 없다.
사용자의 다음 일은 변함없이 A1~A11, B1~B12 채우기. 파일은 전부 미커밋.

**2026-09-14 20:10 갱신.** 1단계 산출물이 만들어졌다. `tools/rv64g/` 의 확장별 명령 표에서 `isa/rv64g.isa`(기본 명령 225 = I 53, Zifencei 1, Zicsr 6 + mret/wfi 2, M 13, A 88, F 30, D 32 / 의사 명령 48 + 실험 4)를 생성하고, 같은 표로 파이썬 참조 인코더(`tools/rv_encode.py`)를 만들어 손계산 벡터 35개와 의사 명령 52개 교차 검증을 통과시켰다(`tools/selftest.py`). 게임 어셈블러 검증 프로그램 `tests/encode_check.asm` 과 기대 바이트 `tests/encode_check.expected.txt`(68워드), 하드웨어 모듈 문서 `components/00-pc` ~ `12-fpu-d`, `99-top`, 검증표 `docs/verification-checklist.md`, 킥오프 `docs/KICKOFF.md` 가 있다. **아직 게임에서 아무것도 검증하지 않았다.** 다음 작업은 사용자가 게임에서 검증표 A1~A10, B1~B12 를 채우는 것이고, 에이전트는 그 결과로 표/문서를 고친다. 파일은 전부 커밋되지 않은 상태다(사용자가 커밋 시점을 정한다).

원래 요약(조사 단계):

사용자는 Steam 게임 Turing Complete(2026-09-14 빌드, buildid 25294874, 8월에 Godot에서 자체 Nim+ImGui 엔진으로 재작성됨)의 아키텍처 샌드박스 안에 RISC-V `RV64G`(RV64I + M + A + F + D + Zicsr + Zifencei)를 **전부** 구현하기로 결정했다. 이번 세션에서는 게임의 어셈블러 정의 문법, 사용 가능한 부품, 세이브/파운드리 구조를 조사해 실현 가능성을 판정했고("가능, 단 F/D는 별도 프로젝트 규모"), 단계 계획을 세웠다. 설계 산출물은 아직 하나도 없다. 첫 작업은 `RV64I` 어셈블러 정의 파일(`.isa`)을 써서 게임 어셈블러가 RISC-V 인코딩(쪼개진 즉시값, PC 상대 오프셋)을 받아들이는지 검증하는 것이다.

핵심 제약: 에이전트는 게임 GUI를 조작할 수 없다(브라우저 확장 미연결, 화면 제어 도구 없음). 회로 배선은 사용자가 게임 안에서 한다. 에이전트가 만들 수 있는 것은 텍스트 산출물(ISA 정의, 어셈블리 테스트 프로그램, 참조 모델/인코더 스크립트, 배선 체크리스트, 문서)이다. 회로 세이브 파일은 문서화되지 않은 바이너리라 직접 생성하지 못한다.

## Codebase Understanding

## Architecture Overview

게임 쪽(코드베이스가 아니라 게임 자료)에서 확인한 사실:

- **게임 폴더**: `C:\Program Files (x86)\Steam\steamapps\common\Turing Complete`. 어셈블러 문서는 `asset\manual\Assembly\Language creation\**\doc.txt`(Overview, Settings, Fields, Instructions, Instructions/Operators, Patterns). 이 문서가 어셈블러 문법의 유일한 1차 자료다. 다시 읽을 것.
- **세이브 폴더**: `%APPDATA%\Turing Complete\`. 레벨 세이브는 `schematics\<level>\<save>\circuit.data`, 커스텀 아키텍처는 `schematics\architecture\<save>\circuit.data` + 같은 폴더의 `sandbox\` 하위 폴더. 레벨에 ISA가 붙는 경우 세이브 폴더에 `spec.isa`(ISA 정의)와 `*.asm`(프로그램)이 생긴다. 커스텀 아키텍처의 ISA 파일 위치는 아직 확인 못 함(사용자가 게임에서 새 아키텍처를 만든 뒤 폴더를 보면 드러남).
- **샌드박스 레벨**: `campaign\sandbox\meta.txt` → `kind = architecture, size = 255`. 보드 크기 255가 최대로 보임(캠페인 레벨은 30~128).
- **어셈블러 정의 파일 구조**: `[settings]`, `[fields]`, `[instructions]`, `[patterns]` 네 섹션. 자세한 문법은 아래 "Key Patterns Discovered".
- **부품 폭**: 2026-07-15 패치 노트 기준 "거의 모든 부품이 2~64비트 폭 지원". 64비트 데이터패스 가능.
- **기본 부품 목록**(`asset\capture\com_*.png` 이름에서 추출): add, inc, neg, mul, div, mod, lsl, lsr, asr, rol, ror, and/or/xor/nand/nor/xnor/not (bit 및 word), and_3_bit, or_3_bit, equal, less_s, less_u, clz, ctz, mux, decoder_1/2/3, register_bit, register_word, register_word_config, counter, imm_counter, ram, ram_latency, load_port, store_port, probe_memory/probe_wire, splitter_word_2/4/8, maker_word_2/4/8, concatenator_2/4/8, constant, static_value, static_indexer, static_eval, config_delay, delay_line_*, switch_bit/word, on, off, halt, keyboard, screen, segment_display, time, level_input_arch, level_output_arch, verilog_input, verilog_output.
- **게임이 제공하는 ISA 예시**: `campaign\symphony\default.isa`(32비트 명령어, 4바이트 기계어 줄, 16개 레지스터), `campaign\overture_4_program\default.isa`(8비트). Symphony 파일이 32비트 고정 길이 명령 정의의 좋은 본보기다.
- **이전 시도 흔적**: 구 Godot 엔진 세이브 `<게임폴더>\godot\app_userdata\Turing Complete\schematics\architecture\@tmp\564\RISC-V\` 에 `circuit.data` 와 `turning-complete-riscv` 항목이 있다. 구 엔진 회로라 새 엔진에서 열리지 않을 가능성이 높다. ISA 텍스트가 있다면 재활용 후보.

## Critical Files

| File | Purpose | Relevance |
|------|---------|-----------|
| `C:\Program Files (x86)\Steam\steamapps\common\Turing Complete\asset\manual\Assembly\Language creation\doc.txt` | 어셈블러 정의 개요 | 문법의 1차 자료 |
| `...\Language creation\Instructions\doc.txt` | 가상 피연산자, 단언문, 비트 슬라이싱, `$start`/`$end` | RISC-V 즉시값 인코딩의 근거 |
| `...\Language creation\Instructions\Operators\doc.txt` | 수식 연산자 표 | 가상 피연산자 계산 |
| `...\Language creation\Patterns\doc.txt` | 매크로 문법 | W형 변형, 폭별 로드/스토어 중복 제거 |
| `...\Language creation\Settings\doc.txt` | name, variant, endianness, 주석 토큰 | `endianness = little` 필요 |
| `C:\Program Files (x86)\Steam\steamapps\common\Turing Complete\campaign\symphony\default.isa` | 32비트 명령 ISA 예시 | 형식 참고 |
| `C:\Users\sw.lee\AppData\Roaming\Turing Complete\schematics\architecture\` | 커스텀 아키텍처 세이브 | RV64G 회로가 살 곳 |
| `C:\Users\sw.lee\AppData\Roaming\Turing Complete\backup\` | 이 세션에서 교체한 세이브의 백업 | 복구용 |
| `C:\Users\sw.lee\Desktop\turing-complete-korean-patch\translation_dict.json` | 한국어 패치 사전 | 게임이 한국어로 보여 주는 오류 문구를 영문 원문으로 역추적할 때 |
| `C:\Users\sw.lee\.claude\projects\C--Users-sw-lee-Desktop-turing-complete-korean-patch\memory\` | 세션 메모리(게임 빌드 검증, 세이브 주입 방법) | 배경 지식 |

## Key Patterns Discovered

게임 어셈블러 정의 문법(문서에서 확인한 것만):

- 명령 정의는 최소 3줄: 문법 줄, 기계어 줄, 설명 줄(`#`로 시작, 필수로 보임). 선택적으로 문법 줄 다음에 가상 피연산자 줄(`%x = 식`)과 단언문 줄(`assert(조건, "메시지")`)이 온다.
- 피연산자는 `%이름(필드|필드)`. 예약 필드는 `label`, `immediate`. 즉시값 타입은 `%a:U6(immediate)`, `%c:U16(immediate | label)` 처럼 `U<비트수>`를 봤다. 부호 있는 타입(`S12`) 표기는 게임 파일에서 못 봤다. 검증 필요.
- 기계어 줄은 `0`/`1` 리터럴과 피연산자 비트. 한 글자 방식은 **피연산자 이름의 첫 글자**를 쓴다(`aaaaa`). 그래서 `%rd`, `%rs1`, `%rs2`는 첫 글자가 같아 한 글자 방식으로는 구분이 안 된다. 비트 슬라이싱 `%name[last:first]`는 전체 이름을 쓰므로 안전하다. 문서: "Bit slicing can be used on multiple operands and intermixed with one bit per character syntax."
- 기계어 줄의 왼쪽이 MSB. 바이트 사이 공백 허용(Symphony 예시). `[settings] endianness = little` 이면 바이트 순서가 뒤집혀 출력된다. RAM 부품에도 별도 endianness 플래그가 있어 이중으로 뒤집힐 수 있으니 주의.
- `$start` = 이 명령 직전의 기계어 오프셋, `$end` = 직후. `%rel = %target - $start` 로 PC 상대 오프셋을 만든다(RISC-V 분기·JAL·AUIPC는 명령 자신의 주소 기준이므로 `$start`).
- 연산자: `! && || == != <u < >=u >= <=u <= >u > ~ & | ^ + - * /u / % << >>`. 단항 마이너스는 `0 - x` 로 처리됨.
- `[patterns]`: `pattern 이름(인자…)` + 문법 치환 줄 + 기계어 치환 줄. 명령 문법 줄에서 `%s[이름("a","b") | 이름("c","d")]` 형태로 열거하면 명령이 여러 개로 전개된다.
- 어셈블러는 정의 목록에서 **처음 매칭되는 문법**을 쓴다. 같은 니모닉의 변형(레지스터형/즉시값형)은 순서에 유의.
- 설명 줄에 `# (31337_id, \`text\`)` 형식이 보이는 것은 게임 번역 시스템용이다. 커스텀 ISA는 `# 설명` 이면 된다.
- 레지스터 필드는 같은 비트 패턴에 여러 이름을 줄 수 있다(예: `x1 00001` 과 `ra 00001`). ABI 이름 지원에 쓴다.

## Work Completed

## Tasks Finished

- [x] 게임 어셈블러 문법 조사(문서 5편 전부 읽음) — RISC-V 인코딩 표현 가능 판정
- [x] 사용 가능한 부품 목록 확보(위 목록) — 64비트 정수 연산 부품 존재 확인
- [x] 세이브·파운드리·샌드박스 폴더 구조 파악
- [x] 확장별 현실성 판정과 구현 순서 제안, 사용자 승인("전부 구현")
- [x] (부수 작업, 같은 세션) 한국어 패치 v0.2.2 릴리즈, 게임 업데이트 감지 워크플로 수정, 캠페인 레벨 정답 주입 — 메모리 파일 참고

## Files Modified

| File | Changes | Rationale |
|------|---------|-----------|
| (RV64G 관련 파일 없음) | — | 조사 단계라 산출물 미작성 |
| `%APPDATA%\Turing Complete\schematics\**` | 캠페인 레벨 세이브에 게임 힌트 정답 주입, 파운드리에 `Hint Overture\*`, `Hint Symphony\*` 부품 추가 | 사용자 요청(캠페인 진행). RV64G와 무관하지만 파운드리 상태를 알아야 함 |
| `C:\Users\sw.lee\Desktop\turing-complete-korean-patch\README.md`, `.github\workflows\check_update.yml`, `last_known_buildid.txt` | v0.2.2 릴리즈, 빌드 ID 감시 | 한국어 패치 프로젝트 |

## Decisions Made

| Decision | Options Considered | Rationale |
|----------|-------------------|-----------|
| 범위: RV64G 전부 | RV64I만, RV64IM, 전부 | 사용자 결정("전부 구현하고 싶은데") |
| 구현 순서 I → M → Zicsr/Zifencei → A → F → D | F/D 먼저, 확장 병렬 | I가 나머지의 기반. F/D는 IEEE-754 연산기를 게이트부터 만들어야 해 가장 큼 |
| 첫 산출물은 `.isa` 파일 | 회로부터 | 회로는 GUI로만 가능. ISA는 에이전트가 만들고 게임 어셈블러로 즉시 검증 가능 |
| 레지스터 파일 = 64비트 RAM + 로드 포트 2개(rs1, rs2) + 스토어 포트 1개(rd) | 레지스터 부품 31개 + 디코더/mux | 부품 수가 압도적으로 적음. x0는 읽기 mux로 0 강제, 쓰기 enable 차단 |
| 단일 사이클, 비파이프라인 | 다단 파이프라인 | 게임 점수 무관, 단순성 우선 |
| 하버드 구조로 시작(프로그램 RAM과 데이터 RAM 분리) | 폰 노이만 단일 RAM | 배선 단순. `fence.i`는 nop. 나중에 필요하면 통합 |
| 즉시값은 타입 없이 `immediate` + 단언문 범위 검사 + 비트 슬라이싱 | `S12` 같은 부호 타입 | 부호 타입 존재 여부 미확인. 슬라이싱은 2의 보수 비트를 그대로 잘라 주므로 타입 없이도 동작할 것으로 기대(검증 항목) |

## Pending Work

## Immediate Next Steps

**갱신된 순서 (1, 2, 4번은 완료):**

1. (완료) 프로젝트 폴더와 구조: `isa/`, `tools/rv64g/`, `tests/`, `components/`, `docs/`.
2. (완료) ISA 정의. 수정은 `tools/rv64g/ext_*.py` 에서 하고 `python tools/gen_isa.py` 로 재생성한다. 손으로 `.isa` 를 고치지 않는다.
3. 사용자: 샌드박스에 아키텍처 `RV64G` 생성 → `isa/rv64g.isa` 붙여넣기 → 오류 문구와 ISA 파일 저장 위치 보고.
4. (완료) 검증 프로그램과 기대 바이트.
5. 검증표 `docs/verification-checklist.md` A1~A10 채우기. A5 실패 시 `isa/rv64g_no_experimental.isa` 사용.
6. B1~B12 부품 실험 결과로 레지스터 파일(04)·LSU(07)·클록(99-top) 방식 확정, 문서 갱신.
7. `components/00-pc` ~ `05-alu` 순서로 사용자가 회로 제작, README 의 검증값으로 단위 테스트. 완성 부품은 파운드리 `RV64G/<이름>`, 허브 업로드 후 폴더에 캡처·링크.
8. `tests/run_*.asm` 실행 프로그램 작성(99-top README 의 표).

원래 목록(참고):

1. 프로젝트 폴더 `C:\Users\sw.lee\Desktop\turing-complete-korean-patch\turing-complete-risc-v` 생성. 구성: `isa\rv64g.isa`, `tests\*.asm`, `tools\` (참조 인코더 스크립트), `docs\` (배선 체크리스트).
2. `rv64i.isa` 작성(아래 부록 A의 인코딩 표 사용). 포함: 레지스터 필드 x0~x31 + ABI 이름, RV64I 전 명령(LUI, AUIPC, JAL, JALR, 분기 6종, 로드 7종, 스토어 4종, OP-IMM 9종, OP 10종, OP-IMM-32 4종, OP-32 5종, FENCE, ECALL, EBREAK), 의사 명령(nop, mv, not, neg, negw, sext.w, seqz, snez, sltz, sgtz, j, jr, ret, call은 2명령, li는 lui+addiw 2명령, beqz/bnez/blez/bgez/bltz/bgtz, bgt/ble/bgtu/bleu).
3. 사용자에게 게임에서 할 일 전달: 샌드박스에서 새 아키텍처(이름 `RV64G`) 생성 → ISA 파일 붙여넣기 → 세이브 폴더에 생긴 파일 위치를 에이전트에게 알려 주기.
4. 어셈블러 검증 프로그램 `tests\encode_check.asm` 작성. 각 형식(R/I/S/B/U/J)에서 한 명령씩, 음수 즉시값, 뒤로/앞으로 분기, 큰 JAL 오프셋 포함. 기대 바이트는 `tools\rv_encode.py`(에이전트가 작성하는 순수 파이썬 참조 인코더)로 계산해 표로 제공. 사용자가 게임의 기계어 뷰와 대조.
5. 검증 결과에 따라 "Blockers/Open Questions"의 항목을 닫는다. 특히 부호 있는 즉시값, `$start` 단위(바이트인지), 64비트 기계어 줄(2명령 의사 명령) 지원 여부.
6. 데이터패스 배선 체크리스트 `docs\01-fetch-decode-regfile.md` 작성: PC 레지스터(64비트) + `+4` 가산기, 프로그램 RAM에서 32비트 페치(little-endian), 명령 필드 분리(splitter로 opcode[6:0], rd[11:7], funct3[14:12], rs1[19:15], rs2[24:20], funct7[31:25]), 즉시값 생성기 5종(I/S/B/U/J, 부호 확장은 bit 31 복제), 레지스터 파일(RAM 방식), 부품별 폭 설정값까지 적는다.
7. 이후 단계는 "Deferred Items"의 로드맵 순서대로.

## Blockers/Open Questions

- [ ] Question: 어셈블러에 부호 있는 즉시값 타입(`S12` 등)이 있는가 — Suggested: `%i(immediate)` + `assert(%i >= -2048 && %i < 2048, ...)` + `%i[11:0]` 로 시도. 음수가 2의 보수로 잘리는지 테스트 프로그램으로 확인.
- [ ] Question: `$start`/`$end` 단위가 바이트인가(비트나 워드가 아닌지) — Suggested: 두 명령짜리 프로그램에서 `jal x0, label` 의 오프셋 바이트를 대조.
- [ ] Question: 기계어 줄이 32비트를 넘어도 되는가(64비트 = 2명령, `li`/`call` 의사 명령용) — Suggested: `li` 를 8바이트 줄로 정의해 어셈블 결과가 두 명령으로 나오는지 확인. 안 되면 의사 명령을 문서로만 제공.
- [ ] Question: 한 RAM 부품에 로드 포트 2개 + 스토어 포트 1개를 붙일 수 있는가, 같은 사이클에 읽기/쓰기 순서는 어떻게 되는가(레지스터 파일 방식의 전제) — Suggested: 사용자가 샌드박스에서 8비트 소형으로 실험. `ram_latency` 부품의 의미도 확인.
- [ ] Question: `mul` 부품이 상위 64비트를 주는가 — Suggested: 안 주면 `mulh/mulhu/mulhsu` 는 32비트 반쪽 곱 4개(또는 64×64 부분곱)로 합성.
- [ ] Question: 커스텀 아키텍처의 ISA 파일 경로와 이름 — Suggested: 사용자가 아키텍처를 만든 뒤 `schematics\architecture\<이름>\` 를 조사.
- [ ] Question: 샌드박스 보드 크기 255에 RV64G 전체(특히 FPU)가 들어가는가 — Suggested: FPU를 파운드리 커스텀 부품으로 캡슐화해 상위 보드 점유를 줄인다.
- [ ] Blocker: 에이전트가 회로를 직접 만들 수 없음 — Needs: 사용자의 게임 내 배선. 에이전트는 배선 체크리스트를 부품 단위로 상세히 써 준다.

## Deferred Items

로드맵(순서 고정, 각 단계는 ISA 항목 + 참조 인코더 + 테스트 프로그램 + 배선 체크리스트 4종 산출물):

- 단계 2: R/I형 ALU(add/sub/and/or/xor/sll/srl/sra/slt/sltu + 즉시값형) — 단계 1 검증 뒤
- 단계 3: 분기 6종, JAL/JALR, LUI/AUIPC — PC mux
- 단계 4: 로드/스토어 11종(lb/lh/lw/ld/lbu/lhu/lwu, sb/sh/sw/sd), 바이트 주소 지정, 부호 확장, 비정렬 접근은 허용 안 함(정렬 단언)
- 단계 5: W형 9종(addiw, slliw, srliw, sraiw, addw, subw, sllw, srlw, sraw) — 하위 32비트 연산 후 부호 확장
- 단계 6: M 확장 13종(mul, mulh, mulhsu, mulhu, div, divu, rem, remu, mulw, divw, divuw, remw, remuw). 특수 규칙: 0으로 나누면 몫 -1(모든 비트 1), 나머지는 피제수. 오버플로(최솟값 / -1)는 몫 최솟값, 나머지 0.
- 단계 7: Zicsr 6종 + ecall/ebreak(halt 부품) + 최소 CSR(cycle, time, instret, mstatus, mtvec, mepc, mcause 정도). Zifencei(`fence.i`)는 nop.
- 단계 8: A 확장(lr/sc/amo* W·D형 22종). 단일 코어라 lr/sc는 항상 성공, amo는 읽기-연산-쓰기 1사이클 또는 2사이클.
- 단계 9: F 확장(단정도, NaN-boxing으로 64비트 FP 레지스터에 저장), 반올림 모드는 RNE부터, fflags/frm CSR.
- 단계 10: D 확장(배정도). 가감산기, 곱셈기(53×53), 나눗셈·제곱근(순차 회로), 변환 8종, 비교, 분류, FMA 4종. 파운드리 커스텀 부품으로 캡슐화.
- 성능(파이프라인, 캐시)은 범위 밖. 게임 점수도 무시.

## Context for Resuming Agent

## Important Context

- 이 작업은 **한국어 패치 저장소와 무관한 새 프로젝트**다. 저장소 안에 RV64G 파일을 만들지 말고 새 폴더를 써라. 이 핸드오프 파일만 저장소의 `.claude\handoffs\` 에 있다(추적되지 않는 파일).
- 에이전트의 역할 분담: 에이전트 = ISA 정의, 참조 인코더, 테스트 프로그램, 배선 체크리스트, 검증 표. 사용자 = 게임 안에서 부품 배치·배선·실행. 사용자에게 게임에서 할 일을 줄 때는 부품 이름(게임 표기), 폭 설정, 핀 연결을 단계별로 적어라.
- 게임은 한국어 패치가 적용돼 있다(`setting_language = Korean`). 사용자가 전해 주는 오류 문구는 한국어다. `translation_dict.json`(`map`: 영문 원문 → 한국어)에서 역검색하면 원문과 발생 위치(`translations\_ids_and_english.txt` 의 섹션)를 알 수 있다.
- 세이브 파일을 만질 일이 있으면(예: 백업) 반드시 게임이 꺼져 있는지 먼저 확인: `tasklist | grep -i turing`. 백업은 `%APPDATA%\Turing Complete\backup\` 에.
- 이 PC에는 `go`, `gh`, `rtk` 가 없다. Python 3.14는 `python` 으로만 있고 `python3` 는 없다. 콘솔이 cp949라 파이썬 출력에 `PYTHONIOENCODING=utf-8` 이 필요하다. Bash 도구에서 `bash` 는 Git Bash이고, PowerShell/subprocess에서 `bash` 는 WSL이 잡힐 수 있다(절대 경로 `C:\Program Files\Git\usr\bin\bash.exe` 사용).
- 사용자 표기 "rc64g" 는 RV64G 로 해석했고 사용자가 이의 없이 진행했다.
- 참조 인코더는 외부 툴체인 없이 순수 파이썬으로 쓴다(이 PC에 riscv-gnu-toolchain 없음). 정확성은 부록 A 표와 RISC-V 비특권 명세로 교차 검증.

## Assumptions Made

- 게임 RAM/로드/스토어 포트가 64비트 폭과 다중 포트를 지원한다(패치 노트의 "2~64비트"에 근거, 미검증).
- 비트 슬라이싱이 음수 값에 대해 2의 보수 비트를 그대로 준다(미검증).
- `$start` 는 바이트 단위 오프셋이다(미검증).
- 샌드박스 보드(255)와 파운드리 캡슐화로 전체 설계가 물리적으로 들어간다(미검증).
- 커스텀 아키텍처에서 ISA를 자유롭게 편집할 수 있다(캠페인 레벨은 `immutable_isa = true` 지만 샌드박스는 아님으로 추정).

## Potential Gotchas

- 기계어 줄 한 글자 방식은 피연산자 **첫 글자**만 본다. `%rd`/`%rs1`/`%rs2` 처럼 첫 글자가 겹치면 잘못 인코딩된다. 슬라이싱(`%rs1[4:0]`)을 쓰거나 이름을 `%d`, `%a`, `%b` 로 하라.
- `endianness = little` 과 RAM 부품의 endianness 플래그가 이중으로 적용될 수 있다. 32비트 페치가 뒤집혀 보이면 둘 중 하나만 켠다.
- 어셈블러는 첫 매칭 문법을 쓴다. `add x1, x2, x3` 와 `add x1, x2, 5` 처럼 필드가 다르면 괜찮지만, 같은 필드 조합에 단언문으로만 구분하려 하면 두 번째 정의는 절대 선택되지 않을 수 있다.
- RISC-V 분기 오프셋은 명령 자신의 주소 기준(`$start`)이고, 항상 짝수(비트 0 생략). JAL도 같다. `jalr` 은 절대 주소 계산 후 최하위 비트를 0으로 만든다.
- SLLI/SRLI/SRAI(RV64)는 shamt 6비트이고 funct7 대신 funct6(bit 31:26)을 본다. W형(slliw 등)은 shamt 5비트에 funct7 7비트다.
- 캠페인에서 사용자가 커스텀 부품을 파운드리에 넣어 둔 상태다(`Hint Overture\*`, `Hint Symphony\*`, `Overture\*`). 지우면 캠페인 세이브가 깨진다. RV64G 부품은 별도 폴더(예: `RV64G\*`)에 만들도록 안내.
- 게임 세이브 폴더는 Steam Cloud 동기화 대상이다. 파일을 밖에서 바꾸면 게임 시작 시 충돌 안내가 뜰 수 있다(로컬 선택).
- 이 세션에서 캠페인 레벨 `overture_4_program` 은 힌트 파일 대신 사용자의 `overture_3` 회로로 채워 두었고, `overture_5_conditionals` 는 주입 파일을 뺐다. 사용자가 캠페인 얘기를 꺼내면 메모리 `game-save-hint-injection.md` 를 읽어라.

## Environment State

## Tools/Services Used

- Python 3.14 (`C:\Python314\python.exe`), PyYAML 설치돼 있음
- Git 2.x (Git Bash), GitHub 자격 증명은 Git Credential Manager에 저장(토큰 출력 금지)
- Steam(게임 설치 경로 위 참고), Steam Cloud 켜짐
- Chrome 확장(claude-in-chrome) 미연결

## Active Processes

- 없음. 게임은 19:23 이후 꺼져 있었음(핸드오프 작성 시점 기준. 재개 시 `tasklist` 로 확인).

## Environment Variables

- `APPDATA` (세이브 경로 계산용), `ProgramFiles(x86)` (Steam 경로). 비밀값 없음.

## Related Resources

- RISC-V 비특권 명세(Unprivileged ISA): https://riscv.org/technical/specifications/ — 인코딩 표(Chapter "RV32/64G Instruction Set Listings")가 부록 A의 원천
- RISC-V 특권 명세(CSR 번호, mstatus 등): 같은 페이지
- 게임 어셈블러 문서: `C:\Program Files (x86)\Steam\steamapps\common\Turing Complete\asset\manual\Assembly\Language creation\`
- 게임 ISA 예시: `campaign\symphony\default.isa`, `campaign\overture_4_program\default.isa`
- 세션 메모리: `C:\Users\sw.lee\.claude\projects\C--Users-sw-lee-Desktop-turing-complete-korean-patch\memory\MEMORY.md`
- 구 버전 RISC-V 시도: `C:\Program Files (x86)\Steam\steamapps\common\Turing Complete\godot\app_userdata\Turing Complete\schematics\architecture\@tmp\564\RISC-V\`

---

## 부록 A. RV64G 인코딩 요약 (참조 인코더와 `.isa` 작성용)

명령은 32비트. `opcode = inst[6:0]`, `rd = inst[11:7]`, `funct3 = inst[14:12]`, `rs1 = inst[19:15]`, `rs2 = inst[24:20]`, `funct7 = inst[31:25]`.

즉시값 형식:

| 형식 | 조립 |
|---|---|
| I | imm[11:0] = inst[31:20] |
| S | imm[11:5] = inst[31:25], imm[4:0] = inst[11:7] |
| B | imm[12] = inst[31], imm[10:5] = inst[30:25], imm[4:1] = inst[11:8], imm[11] = inst[7] (imm[0] = 0) |
| U | imm[31:12] = inst[31:12] |
| J | imm[20] = inst[31], imm[10:1] = inst[30:21], imm[11] = inst[20], imm[19:12] = inst[19:12] (imm[0] = 0) |

모든 즉시값은 부호 확장(64비트).

RV64I:

| 명령 | opcode | funct3 | funct7 / 기타 | 형식 |
|---|---|---|---|---|
| lui | 0110111 | – | – | U |
| auipc | 0010111 | – | – | U |
| jal | 1101111 | – | – | J |
| jalr | 1100111 | 000 | – | I |
| beq/bne/blt/bge/bltu/bgeu | 1100011 | 000/001/100/101/110/111 | – | B |
| lb/lh/lw/ld/lbu/lhu/lwu | 0000011 | 000/001/010/011/100/101/110 | – | I |
| sb/sh/sw/sd | 0100011 | 000/001/010/011 | – | S |
| addi/slti/sltiu/xori/ori/andi | 0010011 | 000/010/011/100/110/111 | – | I |
| slli/srli/srai | 0010011 | 001/101/101 | funct6 000000/000000/010000, shamt = inst[25:20] | I 변형 |
| add/sub | 0110011 | 000 | 0000000/0100000 | R |
| sll/slt/sltu/xor | 0110011 | 001/010/011/100 | 0000000 | R |
| srl/sra | 0110011 | 101 | 0000000/0100000 | R |
| or/and | 0110011 | 110/111 | 0000000 | R |
| addiw | 0011011 | 000 | – | I |
| slliw/srliw/sraiw | 0011011 | 001/101/101 | funct7 0000000/0000000/0100000, shamt = inst[24:20] | I 변형 |
| addw/subw | 0111011 | 000 | 0000000/0100000 | R |
| sllw/srlw/sraw | 0111011 | 001/101/101 | 0000000/0000000/0100000 | R |
| fence | 0001111 | 000 | pred/succ = inst[27:24]/inst[23:20] | I |
| fence.i (Zifencei) | 0001111 | 001 | – | I |
| ecall / ebreak | 1110011 | 000 | imm = 0 / 1 | I |

Zicsr(opcode 1110011): csrrw 001, csrrs 010, csrrc 011, csrrwi 101, csrrsi 110, csrrci 111. csr 번호 = inst[31:20], 즉시값형은 rs1 자리에 5비트 zimm.

M(opcode 0110011, funct7 0000001): mul 000, mulh 001, mulhsu 010, mulhu 011, div 100, divu 101, rem 110, remu 111. W형(opcode 0111011, funct7 0000001): mulw 000, divw 100, divuw 101, remw 110, remuw 111.

A(opcode 0101111, funct3 010 = W, 011 = D, funct5 = inst[31:27], aq = inst[26], rl = inst[25]): lr 00010(rs2 = 0), sc 00011, amoswap 00001, amoadd 00000, amoxor 00100, amoand 01100, amoor 01000, amomin 10000, amomax 10100, amominu 11000, amomaxu 11100.

F/D:

| 명령 | opcode | 비고 |
|---|---|---|
| flw / fld | 0000111 | funct3 010 / 011, I형 |
| fsw / fsd | 0100111 | funct3 010 / 011, S형 |
| fmadd / fmsub / fnmsub / fnmadd | 1000011 / 1000111 / 1001011 / 1001111 | R4형: rs3 = inst[31:27], fmt = inst[26:25] (00 = S, 01 = D), rm = funct3 |
| OP-FP | 1010011 | funct7 = funct5‖fmt. fadd 00000, fsub 00001, fmul 00010, fdiv 00011, fsqrt 01011(rs2 = 0), fsgnj/fsgnjn/fsgnjx 00100(funct3 000/001/010), fmin/fmax 00101(000/001), fcvt.w/wu/l/lu.fmt 11000(rs2 = 0/1/2/3), fcvt.fmt.w/wu/l/lu 11010(rs2 = 0/1/2/3), fmv.x.w·fclass 11100(funct3 000/001, S) 및 fmv.x.d·fclass.d 11100(D), feq/flt/fle 10100(funct3 010/001/000), fmv.w.x 11110(S) / fmv.d.x 11110(D), fcvt.s.d 0100000(rs2 = 1), fcvt.d.s 0100001(rs2 = 0) |

rm(반올림 모드, funct3): 000 RNE, 001 RTZ, 010 RDN, 011 RUP, 100 RMM, 111 DYN(frm CSR). F 값은 64비트 FP 레지스터에 NaN-boxing(상위 32비트 전부 1).

## 부록 B. `.isa` 작성 예시 (검증 전, 문법은 문서 기준)

```
[settings]
name = "RV64G"
endianness = little
line_comments = ["#", ";"]

[fields]

reg
x0 00000
zero 00000
x1 00001
ra 00001
x2 00010
sp 00010
# … x31/t6 까지 (x3 gp, x4 tp, x5-7 t0-t2, x8 s0/fp, x9 s1, x10-17 a0-a7, x18-27 s2-s11, x28-31 t3-t6)

[instructions]

addi %d(reg), %a(reg), %i(immediate)
assert(%i >= -2048 && %i < 2048, "addi: immediate out of range")
%i[11:0] %a[4:0] 000 %d[4:0] 0010011
# rd = rs1 + imm

add %d(reg), %a(reg), %b(reg)
0000000 %b[4:0] %a[4:0] 000 %d[4:0] 0110011
# rd = rs1 + rs2

beq %a(reg), %b(reg), %t(label | immediate)
%o = %t - $start
assert(%o % 2 == 0, "beq: misaligned target")
assert(%o >= -4096 && %o < 4096, "beq: target out of range")
%o[12] %o[10:5] %b[4:0] %a[4:0] 000 %o[4:1] %o[11] 1100011
# if rs1 == rs2 then pc += offset

jal %d(reg), %t(label | immediate)
%o = %t - $start
assert(%o % 2 == 0, "jal: misaligned target")
%o[20] %o[10:1] %o[11] %o[19:12] %d[4:0] 1101111
# rd = pc + 4; pc += offset

lui %d(reg), %i(immediate)
%i[19:0] %d[4:0] 0110111
# rd = sext(imm << 12)
```

검증 항목 1~3(부호 즉시값, `$start` 단위, 64비트 줄)이 닫히기 전에는 위 문법이 그대로 동작한다고 가정하지 말 것.
