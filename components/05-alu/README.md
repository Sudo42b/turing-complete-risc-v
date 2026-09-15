# 05-alu — 64비트 ALU (W형 포함)

## 목적

R형/I형 정수 연산 10종과 W형(32비트 연산 후 부호 확장) 9종. M 확장은 08-muldiv 가 맡고
결과 mux 만 여기서 합친다.

## 핀

| 이름 | 폭 | 방향 | 설명 |
|---|---|---|---|
| `a` | 64 | 입력 | rs1 값 (lui 는 0, auipc 는 pc) |
| `b` | 64 | 입력 | rs2 값 또는 즉시값 (`alu_src_imm`) |
| `funct3` | 3 | 입력 | |
| `funct7_5` | 1 | 입력 | funct7[5]: sub/sra 선택 |
| `is_opimm_any` | 1 | 입력 | is_opimm \| is_opimm32 — 즉시 형식에서는 sub 가 없다 |
| `is_word` | 1 | 입력 | is_opimm32 \| is_op32 |
| `force_add` | 1 | 입력 | load/store/jalr/auipc/lui 주소·덧셈 (funct3 무시하고 add) |
| `y` | 64 | 출력 | |

## 연산 선택

| funct3 | funct7[5]=0 | funct7[5]=1 (R형만) |
|---|---|---|
| 000 | add | sub |
| 001 | sll | |
| 010 | slt | |
| 011 | sltu | |
| 100 | xor | |
| 101 | srl | sra |
| 110 | or | |
| 111 | and | |

`sub_sel = funct3==000 & funct7_5 & ~is_opimm_any`, `sra_sel = funct3==101 & funct7_5` (즉시형 srai 도 funct7[5]=1 이므로 is_opimm_any 로 막지 않는다).

## 내부 설계

```
b_eff   = sub_sel ? Neg(64)(b) : b            (또는 Not + 캐리 1)
sum     = Add(64)(a, b_eff)
sh      = is_word ? b[4:0] : b[5:0]           (5/6비트 Maker)
shl     = Lsl(64)(a, sh)
shr     = Lsr(64)(a, sh)
sar     = Asr(64)(a, sh)
lt      = Less_s(64)(a, b)   → 64비트로 zero-extend (Maker: 63개 0 + 1비트)
ltu     = Less_u(64)(a, b)
res64   = Mux8 by funct3: sum, shl, lt, ltu, Xor, (sra_sel ? sar : shr), Or, And
y64     = force_add ? sum : res64
```

W형: 64비트 부품으로 계산한 뒤 하위 32비트만 취해 부호 확장한다. 시프트만 예외다.

```
srlw    = 하위 32비트를 0으로 상위 확장한 a32 를 Lsr(64) 한 결과의 하위 32비트
sraw    = a 의 하위 32비트를 부호 확장(sext32)한 값을 Asr(64)
sllw    = Lsl(64)(a, sh5) 의 하위 32비트
y       = is_word ? sext32(y64 또는 위 W 결과의 [31:0]) : y64
sext32(v) = Maker(64) ← v[31] ×32 ‖ v[31:0]
```

`Less_s/Less_u` 의 폭이 64 인지, 결과가 1비트인지 부품 설정에서 확인한다.

## 게임에서 만들기

1. `Neg(64)`, `Add(64)`, `Lsl(64)`, `Lsr(64)`, `Asr(64)`, `Xor(64)`, `Or(64)`, `And(64)`, `Less_s(64)`, `Less_u(64)` 를 놓는다.
2. `Mux(64)` 트리(8→1, funct3 비트로 3단)를 만든다.
3. W 경로: `Splitter` 로 하위 32비트, `Maker` 로 부호 확장.
4. 파운드리 `RV64G/ALU`.

## 검증 (a, b → y)

| 연산 | a | b | y |
|---|---|---|---|
| add | 0xFFFF_FFFF_FFFF_FFFF | 1 | 0 |
| sub | 0 | 1 | 0xFFFF_FFFF_FFFF_FFFF |
| sra | 0x8000_0000_0000_0000 | 63 | 0xFFFF_FFFF_FFFF_FFFF |
| srl | 0x8000_0000_0000_0000 | 63 | 1 |
| sltu | 1 | 0xFFFF_FFFF_FFFF_FFFF | 1 |
| slt | 1 | 0xFFFF_FFFF_FFFF_FFFF | 0 |
| addw | 0x7FFF_FFFF | 1 | 0xFFFF_FFFF_8000_0000 |
| srlw | 0xFFFF_FFFF_FFFF_FFFF | 1 | 0x7FFF_FFFF |
| sraw | 0x8000_0000 | 4 | 0xFFFF_FFFF_F800_0000 |

## 상태

**2026-09-15: `tools/gen_alu64.py` 가 파운드리 부품 `RV64G/ALU64` 를 생성한다** (27부품, 52선, 시뮬레이션 400벡터 일치).
핀: a(64) b(64) funct3(3) alt(1) → y(64). 허브 RV32I_ALU 와 같은 구조(디코더 → 스위치 버스). 시프트량 b[5:0] 마스킹은
`static_indexer` 핀 확인 뒤. W형은 감싸는 부품에서. 게임 확인은 검증표 D1~D5.


설계 문서만 있음.
