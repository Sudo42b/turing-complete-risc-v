# 검증 항목

게임 문서만으로는 확정할 수 없어 게임 안에서 직접 확인해야 하는 것들. 결과를 이 파일에 적는다.
확인 방법의 "기대 바이트"는 전부 `tests/encode_check.expected.txt` 에 있다.

## 0. 게임 자료로 미리 확인한 것 (2026-09-14)

게임 실행 파일 `Turing Complete.exe` 안의 어셈블러 오류 문구(`assemble.nim`)와 게임 안 텍스트(한국어 패치 사전
`translation_dict.json` 의 원문, 캠페인 레벨 설명)에서 읽어 낸 사실. 게임 안에서 한 번 더 확인하되, 설계는 이걸 전제로 한다.

| 근거 | 사실 | 영향 |
|---|---|---|
| 오류 문구 "Immediate operand must have size constraint, e.g. %a:U8(immediate)." / "Expected an U for unsigned or S for signed here" | 즉시값 피연산자는 크기 타입이 필수이고, 부호 있는 `S<n>` 타입이 있다 | ISA 전체를 `%i:S12(immediate)` 식으로 재생성했다. 타입이 범위를 검사하므로("Operand value outside of {n}-bit signed range") 범위 단언문은 뺐다. 이전 판(타입 없음)은 A1 에서 바로 실패했을 것 |
| "Only immediates of width 0 to {max_field_size} are allowed", "Only up to {max_field_width}-bit field lengths supported", "Too many virtual operands", "Too many patterns, at most {max_patterns} are allowed", "Too many field types, at most {max_field_types} are allowed" | 폭·개수 상한이 있다. 숫자는 문구에 없다 | A11. 우리가 쓰는 최대 폭은 U32(분기·점프 대상), S33(li32) |
| "Expected slice syntax after field reference in bit pattern" | 기계어 줄의 `%x` 는 반드시 `%x[hi:lo]` 로 쓴다 | 이미 전부 슬라이싱 |
| "The width of instruction '{instruction_name}' is {width} bits, but only multiples of 8 are supported" | 기계어 줄 폭은 8의 배수면 된다 | 32비트, 64비트(li32/la/call/tail) 모두 조건 만족. 64비트 줄이 실제로 되는지는 A5 |
| 문자열 "$start" 존재, 문서의 `$end` | PC 상대 계산 가능 | A3 에서 단위 확인 |
| "Cannot reference private label {name}" | 비공개 라벨 규칙이 있다(`.` 또는 `_` 로 시작하는 이름으로 추정) | 테스트 프로그램 라벨은 `start`, `loop`, `forward` 처럼 일반 이름만 쓴다 |
| 출하 ISA 13개(overture/symphony)는 즉시값을 전부 `:U16`, `:U6` 로 쓰고, 단언문·슬라이싱·가상 피연산자·`[settings]` 옵션은 하나도 쓰지 않는다 | 고급 기능은 문서와 실행 파일 문구로만 뒷받침된다 | A1~A5 가 그 기능들의 첫 실전 검증 |
| Symphony 레벨 설명 "add 3 extra load ports and 3 store ports to the RAM component", 옵코드 load_8/16/32, store_8/16/32 | RAM 하나에 로드·스토어 포트를 여러 개 붙이고, 포트마다 8/16/32비트 폭을 준다 | B1 = 가능, B5 = 폭별 스토어 포트 가능(예상) |
| 캠페인 문구 "The 'zr' register should always be zero (address 0 in the 'Register File')", "{register} ('Register File' address {address})" | 게임 캠페인 자체가 레지스터 파일을 RAM 으로 만든다 | 04-regfile 의 RAM 방식이 게임의 표준 방식 |
| 클록 부품 설명 "Placing the clock will divide cycles into 2 phases. … All memory components load in the early phase and save in the late phase." | 메모리 부품은 앞 단계에 읽고 뒤 단계에 쓴다 | B3 = 같은 틱의 로드는 옛 값을 본다(예상). 단일 사이클 의미론과 맞는다 |
| 부품 설명 "Fast RAM: Fast but high gate cost memory", "Latency RAM: Low gate cost but slow memory", "Dual Load RAM: RAM with an extra load pin", DRAM 설명 "set the pipeline depth of the RAM … loads will take two cycles", 지연 RAM 설명 "reading takes {cycles} cycles (since your circuit has {delay} delay)" | RAM 종류에 따라 읽기 지연이 다르다. Fast RAM 은 게이트 비용만 크고 지연이 없다(예상) | B2: Fast RAM 을 쓰면 단일 사이클. 점수는 무시하므로 모든 RAM 을 Fast RAM 으로 |
| 옛 안내문 "There are also 64 bit versions of the program, the counter, the register and the ram. Notice though, the 64 bit ram takes 1 cycle to load." | 구 엔진 시절 64비트 RAM 은 1사이클 지연이 있었다 | 새 엔진의 Fast RAM(64) 이 지연 없는지 B2 에서 확인 |
| Symphony 레벨 설명 "256 Byte Ram", "'load_8' … loads 8 bits, 'store_16' … stores 16 bits from that address" | RAM 주소는 바이트 단위 | B4 = 바이트 주소(예상). 레지스터 파일은 주소 = idx << 3 |
| 부품 설명 "The file rom outputs the content of a file 8 bytes at a time. The highest 64 bit address (0xFFFFFFFFFFFFFFFF) is special and outputs the length of the file in bytes." | 파일 ROM 부품이 있다 | 나중에 바이너리를 프로그램 RAM 에 넣는 경로 후보 |
| 실행 파일의 부품 id 목록(com_ram, com_load_port, com_pipelined_load_port, com_store_port, com_probe_wire_asm …)에 com_program 이 없고, 레벨 `unlocks_components` 에도 없다. 게임 문구 "Programmable memory component", "Edit program" | 별도 Program 부품이 없다. RAM 이 프로그램 메모리이고 그 편집 아이콘이 IDE(`spec.isa` 탭)를 연다 | 01-ifetch: 빠른 RAM 하나를 프로그램 RAM 으로 쓴다. RAM(`ram_component`)과 포트(`overture_4_program`)는 이미 해결한 레벨이라 열려 있다 |
| 레벨 세이브 폴더에 `spec.isa` 가 `circuit.data` 옆에 있다(`schematics\overture_4_program\Default\`) | 커스텀 아키텍처도 같은 배치일 가능성 | B12 예상: `schematics\architecture\RV64G\spec.isa` |

## A. 어셈블러 (ISA 정의)

| # | 항목 | 확인 방법 | 결과 |
|---|---|---|---|
| A1 | ISA 파일 전체가 오류 없이 로드되는가 | `isa/rv64g.isa` 붙여넣기. 오류가 나면 `isa/rv64g_no_experimental.isa` 로 재시도하고 오류 문구를 그대로 기록 | |
| A2 | 음수 즉시값이 2의 보수로 잘리는가 (`S12` 타입) | `addi x2, x0, -1` → `13 01 f0 ff` | |
| A3 | `$start` 가 바이트 단위인가 | `bne x1, x2, forward` 와 `jal x0, forward` 의 바이트가 기대와 같은가. 다르면 4배/32배 차이를 보고 단위를 추정 | |
| A4 | 뒤로 분기(음수 오프셋) | `bltu x1, x2, start` → 기대값과 비교 | |
| A5 | 32비트를 넘는 기계어 줄(8바이트 의사 명령) | `li32 x1, 0x12345678` 이 `b7 50 34 12 9b 80 80 67` 로 나오는가. 두 워드가 뒤집혀 나오면 리틀 엔디언이 줄 전체에 적용된 것 | |
| A6 | 같은 피연산자를 두 자리에 쓰는 정의 | `fmv.d f1, f2` → `d3 00 21 22` | |
| A7 | 메모리 문법 `imm(reg)`, `(reg)` | `lw x10, -8(x1)`, `lr.w x14, (x2)` | |
| A8 | 반올림 모드 생략/명시 두 문법 | `fadd.d f1, f2, f3` 과 `fadd.s f1, f2, f3, rne` | |
| A9 | 이름 CSR 과 번호 CSR (`U12(csr | immediate)`) | `csrrs x15, mstatus, x0`, `csrrwi x0, 0x305, 3` | |
| A10 | 리틀 엔디언 바이트 순서 | `addi x1, x0, 5` 가 메모리에 `93 00 50 00` 순으로 들어가는가 | |
| A11 | 16비트를 넘는 즉시값 타입(`U20`, `U32`, `S33`)이 허용되는가 | A1 에서 "Only immediates of width 0 to N" 오류가 나면 N 을 기록. N < 33 이면 li32 를 `S32` 로, N < 32 면 분기 대상을 `U<N>` 으로 줄인다(`tools/rv64g/formats.py` 의 `TYPE_OF`) | |

A5 가 실패하면 `isa/rv64g_no_experimental.isa` 를 쓰고 `li32`/`la`/`call`/`tail` 은 손으로 두 명령을 쓴다.

## B. 부품 동작 (레지스터 파일·메모리 설계의 전제)

"예상" 은 0절의 게임 자료에서 나온 것이고, 게임에서 본 결과를 그 뒤에 적는다.

| # | 항목 | 확인 방법 | 결과 |
|---|---|---|---|
| B1 | RAM 한 개에 로드 포트 2개 + 스토어 포트 1개를 붙일 수 있는가 | 8비트 소형 실험 | 예상: 가능 (Symphony 가 로드 4개 + 스토어 3개) / 게임: |
| B2 | 로드 포트 출력이 같은 틱에 나오는가, 1틱 지연인가 | Fast RAM 으로 주소를 바꾼 틱에 값이 바뀌는지 관찰. Latency RAM / DRAM 도 한 번씩 | 예상: Fast RAM 은 지연 없음, Latency RAM 과 DRAM 은 지연 있음 / 게임: |
| B3 | 같은 틱에 스토어와 로드를 하면 로드가 새 값/옛 값 중 무엇을 보는가 | 실험 | 예상: 옛 값 (앞 단계 읽기, 뒤 단계 쓰기) / 게임: |
| B4 | RAM 주소 단위 (바이트 / 워드) 와 포트 폭 설정 범위 | 64비트 포트를 붙였을 때 주소 1 증가가 몇 바이트를 건너뛰는지 | 예상: 바이트 / 게임: |
| B5 | 스토어 포트가 폭별(8/16/32/64) 쓰기를 지원하는가 | 지원하면 sb/sh/sw/sd 를 포트 4개로, 아니면 읽고-합쳐-쓰기 | 예상: 지원 (store_8/16/32 포트) / 게임: |
| B6 | 정렬되지 않은 주소에서 64비트 로드가 되는가 | 주소 1 에서 읽기 | |
| B7 | RAM 의 endianness 플래그와 어셈블러 `endianness = little` 의 상호작용 | 페치한 32비트 워드가 기대 워드와 같은가 (뒤집혀 보이면 둘 중 하나만 켠다) | |
| B8 | `mul` 부품이 상위 64비트를 주는가 | 0xFFFFFFFFFFFFFFFF × 2 | |
| B9 | `div`/`mod` 부품이 부호 있는 연산인가, 0으로 나누면 무엇이 나오는가 | -7 / 2, 7 / 0 | 게임 레벨 문구: 캠페인 나눗셈 레벨은 0 나누기에 0(몫)과 피제수(나머지)를 요구. 기본 부품의 동작은 별개 / 게임: |
| B10 | `add` 부품에 캐리 입력/출력 핀이 있는가 (mulhu 캐리 처리용) | 부품 핀 확인 | 예상: 있음 (레벨 문구 "Carry in", "Carry out") / 게임: |
| B11 | 샌드박스 보드(255) 안에 몇 개 부품이 들어가는가, 파운드리 부품 중첩 깊이 제한 | 대략 확인 | |
| B12 | 커스텀 아키텍처 폴더에 ISA 파일이 어떤 이름으로 저장되는가 | `%APPDATA%\Turing Complete\schematics\architecture\RV64G\` 확인 | 예상: `spec.isa` / 게임: 2026-09-15 아키텍처 생성 직후에는 `circuit.data` 와 `sandbox/sandbox/{sandbox.json,sandbox.v}` 만 생기고 ISA 파일은 없음. 레벨 세이브는 Program 부품이 있을 때 `spec.isa` + `new_program.asm`(CRLF) 을 만듦. 같은 이름으로 미리 넣어 둠. RAM 의 메모리 내용은 `<아키텍처>\sandbox\<부품id>.bin`(레벨별). 게임이 ISA 를 어디서 읽는지는 IDE(RAM 의 "프로그램 편집")를 열어 봐야 확정 |

## C. 결과에 따른 설계 분기

- B2 에서 Fast RAM 에도 지연이 있으면 단일 사이클을 포기하고 2상 클록(페치 틱 / 실행 틱)으로 간다. 게임의 클록 부품이
  한 사이클을 두 단계로 나눠 주므로 그것을 먼저 써 보고, 안 맞으면 `phase` 플립플롭 하나로 만든다.
- B3 가 "새 값"이면 레지스터 파일 쓰기를 `Register` 로 한 단계 늦춘다 (`components/04-regfile`).
- B5 가 "전체 폭만"이면 LSU 에 읽고-합쳐-쓰기 경로를 넣는다 (`components/07-lsu`).
- B8 이 "하위 64비트만"이면 `mulh*` 를 32비트 부분곱 4개로 만든다 (`components/08-muldiv`).
- B11 이 빠듯하면 FPU 를 파운드리 커스텀 부품으로 캡슐화하고, 필요하면 F 를 먼저 완성한 뒤 D 를 별도 부품으로 둔다.
- A11 에서 폭 상한이 나오면 `TYPE_OF` 를 줄이고 재생성한다.
