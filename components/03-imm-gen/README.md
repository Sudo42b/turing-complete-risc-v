# 03-imm-gen — 즉시값 생성기

## 목적

명령 형식(I/S/B/U/J)에 맞게 흩어진 즉시값 비트를 모아 64비트로 부호 확장한다.

## 핀

| 이름 | 폭 | 방향 | 설명 |
|---|---|---|---|
| `instr` | 32 | 입력 | |
| `is_store`, `is_storefp` | 1 | 입력 | S형 선택 |
| `is_branch` | 1 | 입력 | B형 |
| `is_lui`, `is_auipc` | 1 | 입력 | U형 |
| `is_jal` | 1 | 입력 | J형 |
| `imm` | 64 | 출력 | 부호 확장된 즉시값. 기본(선택 없음)은 I형 |

## 즉시값 조립

| 형식 | 비트 구성 (MSB → LSB) | 폭 |
|---|---|---|
| I | instr[31:20] | 12 |
| S | instr[31:25] ‖ instr[11:7] | 12 |
| B | instr[31] ‖ instr[7] ‖ instr[30:25] ‖ instr[11:8] ‖ 0 | 13 |
| U | instr[31:12] ‖ 0×12 | 32 |
| J | instr[31] ‖ instr[19:12] ‖ instr[20] ‖ instr[30:21] ‖ 0 | 21 |

부호 비트는 다섯 형식 모두 `instr[31]` 이다. 그래서 부호 확장은 `instr[31]` 을 필요한 수만큼
복제한 `Maker` 하나로 끝난다.

## 내부 설계

```
sign   = instr[31]
sext52 = Maker(52) ← sign ×52     (64 - 12)
imm_i  = Maker(64) ← sext52 ‖ instr[31:20]
imm_s  = Maker(64) ← sext52 ‖ instr[31:25] ‖ instr[11:7]
imm_b  = Maker(64) ← sign×51 ‖ instr[31] ‖ instr[7] ‖ instr[30:25] ‖ instr[11:8] ‖ 0
imm_u  = Maker(64) ← sign×32 ‖ instr[31:12] ‖ 0×12
imm_j  = Maker(64) ← sign×43 ‖ instr[31] ‖ instr[19:12] ‖ instr[20] ‖ instr[30:21] ‖ 0
imm    = Mux 체인: is_jal ? imm_j : (is_lui|is_auipc) ? imm_u : is_branch ? imm_b : (is_store|is_storefp) ? imm_s : imm_i
```

게임 `Maker` 는 2/4/8 입력이라 계층적으로 묶는다. 1비트 32개로 쪼갠 `instr`(02-decoder 와 공유)에서 필요한 비트를 가져온다.

## 게임에서 만들기

1. 02-decoder 의 1비트 출력 32개를 입력으로 받는다(또는 이 모듈 안에서 다시 쪼갠다).
2. 위 다섯 `Maker` 트리를 만든다. 부호 복제는 같은 선을 여러 입력에 연결하면 된다.
3. `Mux(64)` 4개로 선택.
4. 파운드리 `RV64G/ImmGen`.

## 검증

| instr | 형식 | 기대 imm |
|---|---|---|
| 0xFFF00113 (addi x2,x0,-1) | I | 0xFFFF_FFFF_FFFF_FFFF |
| 0x0021B823 (sd x2,16(x3)) | S | 16 |
| 0xFE208EE3 (beq, -4) | B | -4 |
| 0x123450B7 (lui 0x12345) | U | 0x12345000 |
| 0x0080006F (jal +8) | J | 8 |

## 상태

설계 문서만 있음.
