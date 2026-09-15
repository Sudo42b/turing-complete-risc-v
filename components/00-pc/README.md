# 00-pc — PC 레지스터와 다음 PC 선택

## 목적

현재 명령 주소를 들고 있고, 매 사이클 `pc + 4`, 분기/점프 대상, 트랩 벡터 중 하나로 갱신한다.

## 핀

| 이름 | 폭 | 방향 | 설명 |
|---|---|---|---|
| `clk_en` | 1 | 입력 | 이 틱에 PC 를 갱신할지 (단일 사이클이면 항상 1, 2상 클록이면 실행 틱에만 1) |
| `branch_taken` | 1 | 입력 | 06-branch 가 "분기 성립" 또는 jal/jalr 이면 1 |
| `target` | 64 | 입력 | 06-branch 가 계산한 분기/점프 대상 |
| `trap` | 1 | 입력 | 09-csr 가 ecall/ebreak 를 감지하면 1 |
| `mtvec` | 64 | 입력 | 트랩 벡터 (09-csr) |
| `mret` | 1 | 입력 | mret 실행 중 |
| `mepc` | 64 | 입력 | 복귀 주소 (09-csr) |
| `pc` | 64 | 출력 | 현재 PC (01-ifetch, 03-imm-gen 의 auipc, 06-branch, 09-csr 로) |
| `pc_plus4` | 64 | 출력 | jal/jalr 의 rd 값 |

## 내부 설계

```
pc_reg: Register(64), 초기값 0
pc_plus4 = Add(64)(pc, Constant(64)=4)
next_pc  = Mux(64) 우선순위: trap ? mtvec : mret ? mepc : branch_taken ? target : pc_plus4
pc_reg.in = next_pc, pc_reg.save = clk_en
```

우선순위 mux 는 Mux(64) 3개를 직렬로 잇는다(뒤에 있는 조건이 앞선다).

## 게임에서 만들기

1. `Register(64)` 하나를 놓고 출력에 `pc` 라벨을 붙인다.
2. `Constant(64)` 값 4 와 `Add(64)` 로 `pc_plus4` 를 만든다.
3. `Mux(64)` 세 개를 놓고 선택 핀에 `branch_taken`, `mret`, `trap` 을 이 순서로 건다.
4. 마지막 mux 출력을 레지스터 입력에, `clk_en` 을 저장 핀에 연결한다.
5. 파운드리에 `RV64G/PC` 로 저장한다.

## 검증

- 아무것도 연결하지 않고 틱을 진행하면 `pc` 가 0, 4, 8, … 로 증가해야 한다.
- `branch_taken = 1`, `target = 0x40` 이면 다음 틱에 `pc = 0x40`.
- 리셋은 게임의 회로 리셋으로 대신한다(레지스터 초기값 0).

## 상태

설계 문서만 있음. 회로 미작성.
