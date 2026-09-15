# 10-amo — A 확장

## 목적

lr.w/d, sc.w/d, amoswap/add/xor/and/or/min/max/minu/maxu (.w/.d). 단일 코어라 순서 제약(aq/rl)은 무시한다.

## 핀

| 이름 | 폭 | 방향 |
|---|---|---|
| `addr` | 64 | 입력 (rs1 값, imm 없음) |
| `rs2_val` | 64 | 입력 |
| `funct5` | 5 | 입력 (instr[31:27]) |
| `funct3` | 3 | 입력 (010=W, 011=D) |
| `is_amo`, `clk_en` | 1 | 입력 |
| `old` | 64 | 출력 (rd 에 쓸 값, sc 는 0/1) |
| `mem_read`, `mem_write`, `mem_wdata`, `mem_funct3` | | 07-lsu 로 나가는 요청 |

## 동작 (한 틱에 읽고-계산-쓰기)

```
old  = LSU 로드 (폭은 funct3, W 는 부호 확장)
new  = funct5 에 따라:
       00001 swap: rs2
       00000 add:  old + rs2
       00100 xor:  old ^ rs2
       01100 and:  old & rs2
       01000 or:   old | rs2
       10000 min:  Less_s(old, rs2) ? old : rs2
       10100 max:  Less_s(old, rs2) ? rs2 : old
       11000 minu / 11100 maxu: Less_u 로 동일
       00010 lr:   쓰기 없음, reservation = 1, reserved_addr = addr
       00011 sc:   reservation & (reserved_addr == addr) 이면 rs2 를 쓰고 old = 0, 아니면 old = 1; reservation = 0
mem_write = is_amo & clk_en & (lr 아님) & (sc 면 성공 조건)
```

W 형은 하위 32비트만 쓰고(LSU 의 sw 경로), `old` 는 sext32.

같은 틱에 로드와 스토어를 하는 것이 게임 RAM 에서 되는지(B3)가 전제다. 안 되면 2틱(읽기 틱, 쓰기 틱)으로 만들고
그동안 `clk_en` 을 잡아 둔다.

## 게임에서 만들기

1. `Add/Xor/And/Or(64)`, `Less_s/Less_u(64)`, `Mux(64)` 트리(funct5 비트 5개 중 [4:2] 로 8→1, 나머지 조합).
2. `Register(1)` reservation, `Register(64)` reserved_addr, `Equal(64)`.
3. 파운드리 `RV64G/AMO`.

## 검증

- 주소 0 에 5 저장. `amoadd.d x1, x2, (x0)` (x2=3) → x1=5, 메모리 8.
- `lr.d x1, (x0)` → 8. `sc.d x3, x4, (x0)` (x4=9) → x3=0, 메모리 9. 다시 `sc.d` → x3=1.
- `amomax.w` 로 -1 vs 1 → 1, `amomaxu.w` → 0xFFFF_FFFF.

## 상태

설계 문서만 있음.
