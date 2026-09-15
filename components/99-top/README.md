# 99-top — 상위 보드 통합

## 목적

모듈들을 잇고, 명령 종류별로 mux 선택값을 정한다. 단일 사이클: 한 틱에 페치→디코드→실행→쓰기.

## 데이터 흐름

```
00-pc ──pc──▶ 01-ifetch ──instr──▶ 02-decoder ──필드/제어──▶ (모든 모듈)
                                   03-imm-gen ──imm──▶ ALU b 입력 / 06-branch
04-regfile ──rdata1, rdata2──▶ 05-alu, 06-branch, 07-lsu(wdata), 08-muldiv, 09-csr, 10-amo
05-alu ──y──▶ 07-lsu(addr) / 결과 mux
결과 mux ──wdata──▶ 04-regfile
06-branch ──branch_taken, target──▶ 00-pc
09-csr ──trap/mtvec/mret/mepc──▶ 00-pc
11/12-fpu ──▶ FRegFile, 결과 mux(정수 결과), 09-csr(fflags)
```

## ALU 입력 선택

| 명령 | a | b |
|---|---|---|
| R형, W형 R | rs1 | rs2 |
| I형, W형 I | rs1 | imm |
| load/store/loadfp/storefp/jalr | rs1 | imm (주소) |
| lui | 0 | imm (force_add) |
| auipc | pc | imm (force_add) |
| branch | rs1 | rs2 (비교기는 06-branch, ALU 결과 안 씀) |

`a_sel`: is_auipc ? pc : is_lui ? 0 : rdata1. `b_sel`: alu_src_imm ? imm : rdata2.

## rd 에 쓸 값 (결과 mux)

| 명령 | wdata |
|---|---|
| op/opimm/op32/opimm32 (M 제외) | ALU y |
| M | 08-muldiv y |
| lui/auipc | ALU y (force_add) |
| jal/jalr | pc_plus4 |
| load | 07-lsu rdata |
| csr* | 09-csr rdata (옛 값) |
| amo/lr/sc | 10-amo old |
| fcvt.w/wu/l/lu.*, fmv.x.*, feq/flt/fle, fclass | FPU 정수 결과 |

`reg_write` 는 02-decoder 파생 신호. FP 목적지는 `freg_write` 로 FRegFile 에.

## 메모리 요청 선택

07-lsu 는 정수 로드/스토어, FP 로드/스토어, AMO 세 곳에서 요청을 받는다. `is_amo` 가 우선하고,
그 외에는 `mem_read = is_load | is_loadfp`, `mem_write = is_store | is_storefp`, `wdata = is_storefp ? rs2_f : rdata2`.

## 클록

- 단일 사이클: `clk_en = 1`. RAM 은 전부 Fast RAM 으로 둔다(게임 설명: 게이트 비용만 크고 지연이 없다. 점수는 무시).
- 게임의 클록 부품은 한 사이클을 두 단계로 나누고, 메모리 부품은 앞 단계에 읽고 뒤 단계에 쓴다. 그래서 같은 틱에
  레지스터 파일을 읽고 쓰는 단일 사이클 의미론이 그대로 성립한다(B3).
- Fast RAM 에도 읽기 지연(B2)이 있으면 `phase` = Register(1) 토글. 페치 틱(phase 0)에는 아무것도 쓰지 않고,
  실행 틱(phase 1)에만 `clk_en = 1`. `instr` 를 페치 틱 끝에 Register(32) 에 잡는다.

## 게임에서 만들기

1. 샌드박스에서 아키텍처 `RV64G` 생성, `isa/rv64g.isa` 적용.
2. 파운드리에서 `RV64G/*` 부품을 순서대로 놓는다: PC → Decoder → ImmGen → RegFile → ALU → Branch → LSU → (MulDiv) → (CSR) → (AMO) → (FPU).
3. 위 표대로 mux 를 잇는다.
4. `tests/encode_check.asm` 이 아니라 실행용 프로그램(`tests/run_*.asm`, 작성 예정)으로 레지스터 값을 확인한다.

## 통합 검증 프로그램 (작성 예정)

| 파일 | 내용 | 확인 |
|---|---|---|
| `tests/run_01_alu.asm` | addi/add/sub/시프트/비교 | x1~x10 값 |
| `tests/run_02_branch.asm` | 루프 10회, 조건 분기 6종 | 카운터 레지스터 |
| `tests/run_03_mem.asm` | sd/ld/sb/lb 조합 | 메모리 덤프 |
| `tests/run_04_m.asm` | mul/div 특수 규칙 | |
| `tests/run_05_csr.asm` | ecall 핸들러 → mret | |
| `tests/run_06_fp.asm` | 0.1+0.2, 1/3 | FP 레지스터 비트 패턴 |

## 상태

설계 문서만 있음.
