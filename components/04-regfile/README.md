# 04-regfile — 정수 레지스터 파일

## 목적

x0~x31, 64비트. 같은 틱에 rs1·rs2 를 읽고 rd 에 쓴다. x0 는 항상 0.

## 핀

| 이름 | 폭 | 방향 | 설명 |
|---|---|---|---|
| `rs1`, `rs2`, `rd` | 5 | 입력 | 02-decoder |
| `wdata` | 64 | 입력 | 99-top 의 결과 mux |
| `reg_write` | 1 | 입력 | 02-decoder |
| `clk_en` | 1 | 입력 | 2상 클록이면 실행 틱에만 1 |
| `rdata1`, `rdata2` | 64 | 출력 | |

## 내부 설계 (RAM 방식)

```
rf:     Fast RAM(64), 32 워드 (바이트 주소면 주소 = idx << 3, B4). 지연 없는 종류를 고른다(B2)
load1:  Load port(64), address = rs1, enable = On      → raw1
load2:  Load port(64), address = rs2, enable = On      → raw2
store:  Store port(64), address = rd, data = wdata, enable = reg_write & clk_en & (rd != 0)
rdata1 = Mux(64)(rs1 == 0 ? 0 : raw1)
rdata2 = Mux(64)(rs2 == 0 ? 0 : raw2)
```

`rd != 0` 은 `Or` 트리(5비트) 또는 `Equal(5)` + `Not`. 읽기 쪽 mux 대신 x0 에 절대 쓰지 않는 것만으로도
0 이 유지되지만(초기값 0), 읽기 mux 를 두면 RAM 초기값 보증에 기대지 않아도 된다.

### 대안 (B1 이 실패할 때)

`Register(64)` 31개 + 쓰기 디코더(`Decoder_3` ×… 로 5→32) + 읽기 `Mux(64)` 트리 2벌(31개씩). 부품 수가 10배쯤 늘지만 동작은 확실하다.

## 게임에서 만들기

1. `RAM` 을 놓고 폭 64, 크기 32 로 설정한다.
2. `Load port` 2개, `Store port` 1개를 붙인다.
3. `Equal(5)` + `Constant(5)=0` 으로 `rs1_is_zero`, `rs2_is_zero`, `rd_is_zero` 를 만든다.
4. 쓰기 enable = `And(reg_write, clk_en, Not(rd_is_zero))`.
5. 읽기 mux 2개.
6. 파운드리 `RV64G/RegFile`.

## 검증

- 틱 1: rd=1, wdata=5, reg_write=1. 틱 2: rs1=1 → rdata1=5.
- rd=0, wdata=7, reg_write=1 뒤 rs1=0 → rdata1=0.
- 같은 틱에 rd=2 쓰고 rs2=2 읽으면 옛 값이어야 단일 사이클 의미론이 맞는다(B3). 게임 클록 부품 설명대로 메모리가
  앞 단계에 읽고 뒤 단계에 쓰면 옛 값이 보인다. 새 값이 보이면 쓰기를 틱 끝으로 미루는 `Register` 로 한 단계 지연시킨다.

## 상태

설계 문서만 있음. 게임 자료(검증표 0절)로 B1(포트 여러 개 가능)과 B3(앞 단계 읽기·뒤 단계 쓰기)은 사실상 확인됐고,
B2 는 Fast RAM 을 골라 피한다. 게임 캠페인도 레지스터 파일을 RAM 으로 만든다. 게임에서 재확인 뒤 확정.
