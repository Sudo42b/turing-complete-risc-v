# 09-csr — CSR 파일, 트랩, 카운터

## 목적

Zicsr 6종, ecall/ebreak(트랩), mret, wfi(nop), fflags/frm(FPU 공유), cycle/instret 카운터.
M 모드 하나만 구현한다(U/S 모드 없음).

## 구현하는 CSR

| 이름 | 번호 | 구현 |
|---|---|---|
| fflags | 0x001 | Register(5), FPU 가 OR 로 누적 |
| frm | 0x002 | Register(3) |
| fcsr | 0x003 | frm ‖ fflags 를 합쳐 읽고 나눠 쓴다 |
| cycle / mcycle | 0xC00 / 0xB00 | Counter(64), 매 틱 +1 |
| time | 0xC01 | cycle 과 같은 값(게임 Time 부품을 써도 됨) |
| instret / minstret | 0xC02 / 0xB02 | Counter(64), 실행 틱마다 +1 |
| mstatus | 0x300 | Register(64), MIE(3)·MPIE(7) 비트만 의미 |
| misa | 0x301 | 상수 0x8000_0000_0014_112D (RV64 I M A F D + … ) 읽기 전용 |
| mie, mip | 0x304, 0x344 | Register(64), 인터럽트 없음 → 0 |
| mtvec | 0x305 | Register(64) |
| mscratch | 0x340 | Register(64) |
| mepc | 0x341 | Register(64) |
| mcause | 0x342 | Register(64): ecall=11, ebreak=3 |
| mtval | 0x343 | Register(64) = 0 |
| mvendorid/marchid/mimpid | 0xF11~F13 | 0 |
| mhartid | 0xF14 | 0 |

## 핀

| 이름 | 폭 | 방향 |
|---|---|---|
| `csr_addr` | 12 | 입력 (instr[31:20]) |
| `funct3` | 3 | 입력 |
| `rs1_val` | 64 | 입력 |
| `zimm` | 5 | 입력 (instr[19:15]) |
| `is_csr`, `is_ecall`, `is_ebreak`, `is_mret` | 1 | 입력 |
| `pc` | 64 | 입력 |
| `fflags_set` | 5 | 입력 (FPU 예외 플래그, OR 누적) |
| `clk_en` | 1 | 입력 |
| `rdata` | 64 | 출력 (rd 에 쓸 옛 값) |
| `trap`, `mtvec`, `mret`, `mepc` | 1/64/1/64 | 출력 (00-pc) |
| `frm` | 3 | 출력 (FPU) |

## 동작

```
old   = 읽기 mux (csr_addr 를 Equal(12) 로 판별, 구현한 CSR 만큼)
src   = funct3[2] ? zext(zimm) : rs1_val
new   = funct3[1:0] == 01 ? src : funct3[1:0] == 10 ? old | src : old & ~src
write = is_csr & clk_en & ~(funct3[1:0]==10/11 이고 src 가 x0/0 인 경우는 쓰지 않아도 됨) & (읽기 전용 CSR 이 아님)
rdata = old
```

트랩: `trap = is_ecall | is_ebreak`. 그 틱에 `mepc = pc`, `mcause = is_ecall ? 11 : 3`, `mstatus.MPIE = MIE`, `MIE = 0`.
mret: `mstatus.MIE = MPIE`, PC 는 `mepc` (00-pc 가 처리).
wfi: nop. `ebreak` 를 halt 로 쓰고 싶으면 `is_ebreak` 를 게임 `Halt` 부품에 연결하는 옵션을 둔다.

## 게임에서 만들기

1. 레지스터 9개(`Register(64)` 또는 필요한 폭), `Counter(64)` 2개.
2. `Equal(12)` 로 CSR 판별, `Mux(64)` 트리로 읽기.
3. 쓰기 값 계산 `Or/And/Not(64)` + `Mux`.
4. 파운드리 `RV64G/CSR`.

## 검증

- `csrrw x1, mscratch, x2` (x2=7) 뒤 `csrr x3, mscratch` → 7.
- `csrrsi x0, mstatus, 8` → mstatus.MIE=1. `csrrci` 로 해제.
- `ecall` 뒤 pc = mtvec, mepc = ecall 주소, mcause = 11. `mret` 뒤 pc = mepc.
- 두 명령 실행 뒤 `rdinstret` → 2 (카운터 기준 조정).

## 상태

설계 문서만 있음.
