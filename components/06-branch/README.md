# 06-branch — 분기 비교기와 점프 대상

## 목적

B형 6종의 조건 판정, jal/jalr 대상 계산, `branch_taken` 과 `target` 을 00-pc 에 넘긴다.

## 핀

| 이름 | 폭 | 방향 | 설명 |
|---|---|---|---|
| `a`, `b` | 64 | 입력 | rs1, rs2 값 |
| `funct3` | 3 | 입력 | |
| `is_branch`, `is_jal`, `is_jalr` | 1 | 입력 | |
| `pc` | 64 | 입력 | |
| `imm` | 64 | 입력 | 03-imm-gen (B형 또는 J형/I형) |
| `branch_taken` | 1 | 출력 | |
| `target` | 64 | 출력 | |

## 조건 판정

| funct3 | 조건 |
|---|---|
| 000 beq | eq |
| 001 bne | ~eq |
| 100 blt | lt_s |
| 101 bge | ~lt_s |
| 110 bltu | lt_u |
| 111 bgeu | ~lt_u |

```
eq   = Equal(64)(a, b)
lt_s = Less_s(64)(a, b)
lt_u = Less_u(64)(a, b)
base = funct3[2] ? (funct3[1] ? lt_u : lt_s) : eq       (Mux 2단, 1비트)
cond = base ^ funct3[0]
branch_taken = (is_branch & cond) | is_jal | is_jalr
```

## 대상 계산

```
t_rel = Add(64)(pc, imm)                    (branch, jal)
t_reg = Add(64)(a, imm) & ~1                (jalr: 최하위 비트 0)
target = is_jalr ? t_reg : t_rel
```

`& ~1` 은 `And(64)` + `Constant(64) = 0xFFFF_FFFF_FFFF_FFFE`.

## 게임에서 만들기

1. `Equal(64)`, `Less_s(64)`, `Less_u(64)` 와 1비트 `Mux` 2개, `Xor` 1개.
2. `Add(64)` 2개, `And(64)`, `Mux(64)`.
3. 파운드리 `RV64G/Branch`.

## 검증

- a=5, b=5, funct3=000 → cond=1. funct3=001 → 0.
- a=-1, b=1: blt → 1, bltu → 0.
- pc=8, imm=-4, is_branch, cond=1 → target=4.
- is_jalr, a=0x1001, imm=0 → target=0x1000.

## 상태

설계 문서만 있음.
