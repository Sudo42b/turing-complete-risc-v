# 08-muldiv — M 확장

## 목적

mul, mulh, mulhsu, mulhu, div, divu, rem, remu 와 W형 5종. `is_m = (is_op|is_op32) & funct7==0000001`.

## 핀

| 이름 | 폭 | 방향 |
|---|---|---|
| `a`, `b` | 64 | 입력 |
| `funct3` | 3 | 입력 |
| `is_word` | 1 | 입력 |
| `y` | 64 | 출력 |

## 연산

| funct3 | 64비트 | W형 |
|---|---|---|
| 000 | mul (하위 64) | mulw |
| 001 | mulh (상위 64, s×s) | |
| 010 | mulhsu (s×u) | |
| 011 | mulhu (u×u) | |
| 100 | div | divw |
| 101 | divu | divuw |
| 110 | rem | remw |
| 111 | remu | remuw |

## 곱셈

`Mul(64)` 이 하위 64비트만 주면(B8) 상위 64비트는 32비트 부분곱으로 만든다.

```
al = a[31:0], ah = a[63:32], bl, bh (전부 64비트로 zero-extend)
p0 = al*bl, p1 = ah*bl, p2 = al*bh, p3 = ah*bh        (각각 64비트 안에 들어감)
mid = p1 + p2 + (p0 >> 32)                             (최대 66비트: 캐리 2개를 따로 받는다, B10)
mulhu = p3 + (mid >> 32) + (mid 캐리 << 32)
mulh   = mulhu(a,b) - (a<0 ? b : 0) - (b<0 ? a : 0)     (Less_s 로 부호 판정, Mux, Sub)
mulhsu = mulhu(a,b) - (a<0 ? b : 0)
```

`Add(64)` 에 캐리 출력이 없으면 `Less_u(sum, p1)` 로 캐리를 검출한다(합이 피연산자보다 작으면 넘침).

## 나눗셈

게임 `Div`/`Mod` 가 부호 없는 연산이면(B9) 부호는 밖에서 처리한다.

```
neg_a = a[63], neg_b = b[63]
ua = neg_a ? Neg(a) : a, ub = neg_b ? Neg(b) : b
q  = Div(64)(ua, ub), r = Mod(64)(ua, ub)
div  = (neg_a ^ neg_b) ? Neg(q) : q
rem  = neg_a ? Neg(r) : r
divu = Div(64)(a, b), remu = Mod(64)(a, b)
```

명세의 특수 규칙을 Mux 로 덮는다.

| 조건 | div | divu | rem | remu |
|---|---|---|---|---|
| b == 0 | -1 (전부 1) | 전부 1 | a | a |
| a == INT_MIN, b == -1 (div/rem 만) | a | | 0 | |

`b == 0` 은 `Equal(64)`; 오버플로는 `Equal(a, 0x8000…)` & `Equal(b, 0xFFFF…)`.

W형은 하위 32비트를 부호(또는 무부호) 확장한 뒤 같은 회로에 넣고 결과를 sext32 한다. divuw/remuw 는 zero-extend 입력.

## 게임에서 만들기

1. `Mul(64)` 4개(또는 1개, B8 에 따라), `Add(64)` 몇 개, 캐리 검출 `Less_u`.
2. `Div(64)`, `Mod(64)` 각 2개(부호/무부호 경로), `Neg(64)` 4개, 특수 규칙 `Equal` 3개, `Mux(64)` 트리.
3. 파운드리 `RV64G/MulDiv`.

## 검증

| 연산 | a | b | y |
|---|---|---|---|
| mulhu | 0xFFFF_FFFF_FFFF_FFFF | 0xFFFF_FFFF_FFFF_FFFF | 0xFFFF_FFFF_FFFF_FFFE |
| mulh | -1 | -1 | 0 |
| mulhsu | -1 | 0xFFFF_FFFF_FFFF_FFFF | -1 (0xFFFF…) |
| div | -7 | 2 | -3 |
| rem | -7 | 2 | -1 |
| div | 7 | 0 | -1 |
| rem | 7 | 0 | 7 |
| div | INT_MIN | -1 | INT_MIN |
| rem | INT_MIN | -1 | 0 |
| divw | 0x8000_0000 (as -2^31) | -1 | 0xFFFF_FFFF_8000_0000 |

## 상태

설계 문서만 있음.
