# 02-decoder — 명령 필드 분리와 제어 신호

## 목적

32비트 명령을 필드로 쪼개고, opcode 를 판별해 각 모듈이 쓰는 1비트 제어 신호를 만든다.
funct3/funct7 의 세부 해석은 각 연산 모듈이 한다(ALU, 분기, LSU 등).

## 핀

입력: `instr` (32)

출력 필드:

| 이름 | 폭 | 비트 |
|---|---|---|
| `opcode` | 7 | [6:0] |
| `rd` | 5 | [11:7] |
| `funct3` | 3 | [14:12] |
| `rs1` | 5 | [19:15] |
| `rs2` | 5 | [24:20] |
| `funct7` | 7 | [31:25] |
| `rs3` | 5 | [31:27] (R4형) |
| `fmt` | 2 | [26:25] (FP) |
| `shamt6` | 6 | [25:20] (RV64 시프트) |
| `csr` | 12 | [31:20] |

출력 제어 (opcode 판별, one-hot):

| 이름 | opcode | 뜻 |
|---|---|---|
| `is_lui` | 0110111 | |
| `is_auipc` | 0010111 | |
| `is_jal` | 1101111 | |
| `is_jalr` | 1100111 | |
| `is_branch` | 1100011 | |
| `is_load` | 0000011 | |
| `is_store` | 0100011 | |
| `is_opimm` | 0010011 | |
| `is_op` | 0110011 | R형 (M 포함) |
| `is_opimm32` | 0011011 | W형 즉시 |
| `is_op32` | 0111011 | W형 R (M 포함) |
| `is_miscmem` | 0001111 | fence, fence.i |
| `is_system` | 1110011 | csr*, ecall, ebreak, mret, wfi |
| `is_amo` | 0101111 | A |
| `is_loadfp` | 0000111 | flw/fld |
| `is_storefp` | 0100111 | fsw/fsd |
| `is_opfp` | 1010011 | F/D 연산 |
| `is_fma` | 10x0x11 | fmadd/fmsub/fnmsub/fnmadd (opcode[6:4]=100, [1:0]=11) |

파생 신호:

| 이름 | 식 |
|---|---|
| `reg_write` | is_lui \| is_auipc \| is_jal \| is_jalr \| is_load \| is_opimm \| is_op \| is_opimm32 \| is_op32 \| is_system·(funct3≠0) \| is_amo \| is_opfp·(rd 가 정수인 경우: fcvt.w/l, fmv.x, feq/flt/fle, fclass) |
| `freg_write` | is_loadfp \| is_fma \| is_opfp·(rd 가 FP 인 경우) |
| `is_word_op` | is_opimm32 \| is_op32 |
| `is_m` | (is_op \| is_op32) · (funct7 == 0000001) |
| `alu_src_imm` | is_opimm \| is_opimm32 \| is_load \| is_store \| is_jalr \| is_loadfp \| is_storefp |
| `is_ecall` | is_system · funct3==0 · csr==0x000 |
| `is_ebreak` | is_system · funct3==0 · csr==0x001 |
| `is_mret` | is_system · funct3==0 · csr==0x302 |
| `is_csr` | is_system · funct3≠0 |

## 내부 설계

- `Splitter` 로 비트를 뽑는다. 게임 splitter 는 2/4/8 분할이므로 32비트를 8비트 4개로 쪼갠 뒤
  필요한 경계(7, 5, 3, 5, 5, 7)를 `Maker`/`Splitter` 조합으로 다시 만든다. 가장 간단한 방법은
  32비트를 1비트 32개로 완전히 쪼개고(`Splitter_8` ×4 → `Splitter_bit` 계열) 필드마다 `Maker` 로 묶는 것이다.
- opcode 판별은 `Equal(7)` + `Constant(7)` 한 쌍씩. 18개.
- 파생 신호는 `Or`/`And` 게이트.

## 게임에서 만들기

1. `instr` 입력을 1비트 32개로 쪼갠다.
2. 표의 필드마다 `Maker` 로 묶어 라벨을 붙인다.
3. opcode 상수 18개와 `Equal(7)` 로 `is_*` 를 만든다.
4. 파생 신호 게이트를 놓는다.
5. 파운드리 `RV64G/Decoder`.

## 검증

`instr = 0x00500093`(addi x1, x0, 5)에서 `is_opimm = 1`, `rd = 1`, `rs1 = 0`, `funct3 = 0`, 즉시값 필드 [31:20] = 5.
`instr = 0xFE208EE3`(beq x1, x0, -4)에서 `is_branch = 1`, `rs1 = 1`, `rs2 = 0`.

## 상태

설계 문서만 있음.
