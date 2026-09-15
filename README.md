# Turing Complete RISC-V (RV64G)

게임 [Turing Complete](https://store.steampowered.com/app/1444480/) 의 아키텍처 샌드박스 안에
RISC-V `RV64G`(RV64I + M + A + F + D + Zicsr + Zifencei)를 만드는 프로젝트입니다.

산출물은 두 갈래입니다.

| 갈래 | 위치 | 만드는 주체 |
|---|---|---|
| 어셈블러 정의(ISA), 참조 인코더, 테스트 프로그램, 설계 문서 | `isa/`, `tools/`, `tests/`, `components/*/README.md` | 텍스트라 에이전트가 만들고 여기서 관리 |
| 회로 | 게임 안(파운드리 커스텀 부품, 아키텍처 세이브) | 게임 GUI로만 만들 수 있음. 완성되면 `components/<모듈>/` 에 허브 업로드 정보와 캡처를 남김 |

컴포넌트(하드웨어 모듈)와 확장(ISA 조각)은 각각 따로 허브에 올릴 수 있도록 폴더 단위로 나눠 둡니다.

## 폴더 구성

```
isa/
  rv64g.isa                  게임에 넣는 ISA 정의 (전체, 생성 파일)
  rv64g_no_experimental.isa  8바이트 의사 명령을 뺀 안정판
  parts/                     확장별 조각 (00_settings, 10_fields, 20_rv64i, 30_zifencei,
                             31_zicsr, 40_m, 50_a, 60_f, 70_d, 90_pseudo, 95_pseudo_experimental)
tools/
  rv64g/                     명령 표(확장별 모듈) + .isa 생성기 + 참조 인코더
  gen_isa.py                 isa/ 를 다시 만든다
  rv_encode.py               .asm -> 기대 기계어 대조표
  selftest.py                표·인코더·생성기 자체 검사
tests/
  encode_check.asm           게임 어셈블러 검증 프로그램
  encode_check.expected.txt  위 프로그램의 기대 바이트 (참조 인코더 출력)
components/                  하드웨어 모듈별 설계 문서 (핀, 내부 구조, 배선 순서, 검증)
docs/
  KICKOFF.md                 프로젝트 킥오프 메시지
  verification-checklist.md  게임 어셈블러·부품 동작 검증 항목
```

## 빠른 시작

```bash
python tools/selftest.py          # 표와 인코더가 서로 맞는지 확인
python tools/gen_isa.py           # isa/ 재생성 (표를 고친 뒤)
python tools/rv_encode.py tests/encode_check.asm -o tests/encode_check.expected.txt
```

게임에서:

1. 샌드박스에서 새 아키텍처 `RV64G` 를 만든다.
2. `isa/rv64g.isa` 내용을 ISA 편집 창에 붙여 넣는다. 오류가 나면 `isa/rv64g_no_experimental.isa` 로 바꿔 본다.
3. `tests/encode_check.asm` 을 프로그램으로 넣고 어셈블한 뒤, 기계어를 `tests/encode_check.expected.txt` 와 줄 단위로 비교한다.
4. 결과를 `docs/verification-checklist.md` 의 항목에 기록한다.

## ISA 정의가 게임 문법에 기대는 것

게임 어셈블러 문서(`asset/manual/Assembly/Language creation/`)와 게임 실행 파일의 어셈블러 오류 문구에서
확인한 기능만 씁니다. 근거는 `docs/verification-checklist.md` 0절.

- 비트 슬라이싱 `%o[10:5]` 로 RISC-V 의 쪼개진 즉시값(B/J형)을 표현
- 가상 피연산자 `%o = %t - $start` 로 PC 상대 오프셋
- 단언문으로 즉시값 범위·정렬 검사
- `endianness = little`
- 즉시값에는 크기 타입 필수: `%i:S12(immediate)`, `%s:U6(immediate)`, `%t:U32(immediate | label)`.
  타입이 범위를 검사하므로 범위 단언문은 따로 두지 않는다. 종류별 타입은 `tools/rv64g/formats.py` 의 `TYPE_OF`
- 피연산자 이름은 전부 한 글자(`%d %a %b %c %i %t %s %n %z %r`). 한 글자 방식 기계어 표기가 이름 첫 글자만 보기 때문

## 구현 순서

| 단계 | 내용 | 관련 폴더 |
|---|---|---|
| 1 | ISA 정의 검증 (어셈블러가 RISC-V 인코딩을 받는지) | `isa/`, `tests/`, `docs/verification-checklist.md` |
| 2 | PC, 페치, 디코더, 즉시값 생성기, 레지스터 파일, ALU (R/I형) | `components/00-pc` ~ `05-alu` |
| 3 | 분기·점프, lui/auipc | `components/06-branch` |
| 4 | 로드/스토어 11종 | `components/07-lsu` |
| 5 | W형 명령 | `components/05-alu` |
| 6 | M 확장 | `components/08-muldiv` |
| 7 | Zicsr + ecall/ebreak/mret, Zifencei | `components/09-csr` |
| 8 | A 확장 | `components/10-amo` |
| 9 | F 확장 | `components/11-fpu-f` |
| 10 | D 확장 | `components/12-fpu-d` |
| 통합 | 상위 보드 | `components/99-top` |

단일 사이클, 비파이프라인, 하버드 구조(프로그램 RAM 과 데이터 RAM 분리)로 시작합니다.
게임 RAM 에 읽기 지연이 있으면 2단계(페치/실행) 상태 기계로 바꿉니다. 검증 항목 참고.

## 명령 수

| 확장 | 기본 명령 | 비고 |
|---|---|---|
| RV64I | 53 | jalr 두 문법 포함, fence/ecall/ebreak 포함 |
| Zifencei | 1 | |
| Zicsr | 6 (+ mret, wfi) | |
| M | 13 | |
| A | 88 | 11종 × W/D × aq/rl 4가지 |
| F | 30 | |
| D | 32 | fcvt.s.d / fcvt.d.s 포함 |
| 의사 명령 | 48 (+4 실험) | li 는 12비트 전용, li32/la/call/tail 은 8바이트 줄 |

## 참고

- RISC-V 비특권·특권 명세: https://riscv.org/technical/specifications/
- 게임 어셈블러 문서: `<게임 폴더>/asset/manual/Assembly/Language creation/**/doc.txt`
- 게임 ISA 예시: `<게임 폴더>/campaign/symphony/default.isa`
