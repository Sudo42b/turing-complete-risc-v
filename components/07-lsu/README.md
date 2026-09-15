# 07-lsu — 데이터 RAM 과 로드/스토어

## 목적

lb/lh/lw/ld/lbu/lhu/lwu, sb/sh/sw/sd (정수 11종) 와 flw/fld/fsw/fsd 의 메모리 접근.
바이트 주소, 리틀 엔디언. 비정렬 접근은 게임 포트가 허용하면 그대로, 아니면 정렬 요구.

## 핀

| 이름 | 폭 | 방향 | 설명 |
|---|---|---|---|
| `addr` | 64 | 입력 | ALU 결과 (rs1 + imm) |
| `wdata` | 64 | 입력 | rs2 (또는 FP 레지스터 값) |
| `funct3` | 3 | 입력 | [1:0] 폭 00=8 01=16 10=32 11=64, [2] 1=zero-extend |
| `mem_read` | 1 | 입력 | is_load \| is_loadfp \| AMO 읽기 |
| `mem_write` | 1 | 입력 | is_store \| is_storefp \| AMO 쓰기 |
| `clk_en` | 1 | 입력 | |
| `rdata` | 64 | 출력 | 부호/제로 확장된 값 |

## 내부 설계

```
dram:  RAM (바이트 단위, 크기는 샌드박스 허용 범위에서 크게)
load:  Load port(64), address = addr, enable = mem_read     → raw64 (리틀 엔디언 8바이트)
b8  = raw64[7:0], b16 = raw64[15:0], b32 = raw64[31:0]
sx8  = Maker(64) ← raw64[7]×56 ‖ b8      zx8  = 0×56 ‖ b8
sx16 = …[15]×48 ‖ b16                   zx16
sx32 = …[31]×32 ‖ b32                   zx32
rdata = Mux by funct3: 000 sx8, 001 sx16, 010 sx32, 011 raw64, 100 zx8, 101 zx16, 110 zx32
```

스토어는 B5 결과에 따라 둘 중 하나. Symphony 레벨이 store_8/16/32 를 폭별 스토어 포트 3개로 만들게 하므로 첫째 방식이 유력하다.

- 포트가 폭별 쓰기를 지원하면: `Store port(8/16/32/64)` 4개를 같은 주소·데이터에 붙이고
  enable = `mem_write & clk_en & (funct3[1:0] == 해당 폭)`.
- 전체 폭만 되면: `raw64` 를 읽어 하위 8/16/32비트만 `wdata` 로 바꾼 값을 `Store port(64)` 로 쓴다
  (Mux 3단). 같은 틱에 읽고 쓰기가 되는지는 B3.

## 게임에서 만들기

1. `RAM` 을 놓고 바이트 폭, 크기 설정. 엔디언 플래그는 리틀(B7).
2. `Load port(64)` 하나, `Store port` 4개(또는 1개 + 합치기 경로).
3. 확장 `Maker` 6개와 `Mux(64)` 트리.
4. 파운드리 `RV64G/LSU`.

## 검증

- sd 0x1122_3344_5566_7788 → 주소 0. lb 주소 0 → 0xFFFF…FF88 (부호), lbu → 0x88, lh 주소 2 → 0x5566, lwu 주소 4 → 0x1122_3344.
- sb 0xAA 주소 3 뒤 ld 주소 0 → 0x1122_3344_AA66_7788.

## 상태

설계 문서만 있음. 게임 자료(검증표 0절)로 B4(바이트 주소)·B5(폭별 포트)는 예상이 섰다. 게임에서 재확인 뒤 스토어 경로 확정.
