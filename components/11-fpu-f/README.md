# 11-fpu-f — F 확장 (단정도)

## 목적

IEEE-754 binary32 연산 30종(F)과 FP 레지스터 파일 f0~f31(64비트, 단정도 값은 NaN-boxing).
D 확장(12-fpu-d)이 같은 구조를 53비트 가수로 반복하므로, 여기서 만드는 하위 모듈은 폭만 바꿔 재사용할 수 있게 설계한다.

## 하위 모듈 (각각 파운드리 부품, 허브 업로드 단위)

| 폴더/부품 | 역할 |
|---|---|
| `RV64G/FRegFile` | 04-regfile 과 같은 RAM 방식, 32 × 64비트, 읽기 포트 3개(rs1, rs2, rs3), x0 특례 없음 |
| `RV64G/F_Unpack` | 32비트 → 부호 1, 지수 8, 가수 24(숨은 1 포함), 분류 플래그(zero, inf, nan, qnan, subnormal). NaN-box 검사: 상위 32비트가 전부 1 이 아니면 canonical NaN 으로 취급 |
| `RV64G/F_Pack` | 부호·지수·가수 → 32비트 + NaN-boxing(상위 32비트 1) |
| `RV64G/F_Round` | 가수+guard/round/sticky → 반올림 5모드(rm), 오버플로/언더플로 처리, 예외 플래그(NV/DZ/OF/UF/NX) 출력 |
| `RV64G/F_AddSub` | 지수 정렬(Lsr 로 작은 쪽 시프트, sticky 수집), 가수 가감, 정규화(Clz 부품으로 선행 0 계산 → Lsl), F_Round |
| `RV64G/F_Mul` | 24×24 가수 곱(Mul(64) 하나), 지수 합, 정규화, F_Round |
| `RV64G/F_Div` | 24비트 복원 나눗셈을 조합 회로로 펼침(단계 26개: 몫 24비트 + guard + round). 각 단계 = Sub + Less_u + Mux. 또는 게임 `Div(64)` 로 (가수<<26) / 가수 를 한 번에 구해 몫 26비트 + sticky(Mod≠0) 를 얻는다. 후자가 훨씬 작다 |
| `RV64G/F_Sqrt` | 디지트 단위 제곱근 26단계 조합 회로. 또는 뉴턴 반복 없이 Div 부품 기반 근사는 불가하므로 이 모듈은 조합 체인이 필요 |
| `RV64G/F_FMA` | 정확한 융합 곱셈-덧셈: 48비트 곱 + 정렬된 덧수(최대 74비트) → 64비트 부품 2개로 나눠 처리(하위/상위 워드 + 캐리). 첫 구현에서는 Mul 후 AddSub 를 두 번 반올림하는 "비융합" 버전으로 만들고 표기해 둔다 |
| `RV64G/F_Cmp` | feq/flt/fle (NaN 처리: 조용한 NaN 은 feq 에서 NV 없음, 시그널링 NaN 은 NV), fmin/fmax (NaN 규칙, -0 < +0) |
| `RV64G/F_Cvt` | fcvt.w/wu/l/lu.s (반올림·범위 밖은 최대/최소값 + NV), fcvt.s.w/wu/l/lu (정수 → float: Clz 로 정규화 후 F_Round) |
| `RV64G/F_Misc` | fsgnj/fsgnjn/fsgnjx, fmv.x.w(부호 확장), fmv.w.x(NaN-box), fclass(10비트 마스크) |

## 상위 배선

```
rs1_f, rs2_f, rs3_f  ← FRegFile
연산 선택 ← 02-decoder 의 is_opfp/is_fma/is_loadfp/is_storefp + funct7[6:2] + rs2(변환 종류) + funct3
결과 mux → FRegFile 쓰기(freg_write) 또는 정수 rd 쓰기(fcvt.w*, fmv.x.w, feq/flt/fle, fclass)
fflags_set → 09-csr 에 OR 누적, rm: funct3 == 111 이면 09-csr 의 frm 사용
```

## 구현 순서 권장

1. FRegFile, F_Unpack, F_Pack, F_Misc, flw/fsw (LSU 재사용) — 값 이동만으로 프로그램이 돈다
2. F_Cmp, F_Cvt(정수↔float)
3. F_Round + F_AddSub + F_Mul
4. F_Div (Div 부품 방식), F_Sqrt
5. F_FMA (비융합 → 융합)

## 검증

- 1.0f = 0x3F800000, 2.0f = 0x40000000: fadd → 0x40400000 (3.0f)
- 0.1f + 0.2f = 0x3E99999A (RNE)
- 1.0f / 3.0f = 0x3EAAAAAB
- sqrt(2.0f) = 0x3FB504F3
- fcvt.w.s(-1.5f, rtz) = -1, rne = -2, rdn = -2, rup = -1
- fclass(-0.0f) = 0x008, fclass(+inf) = 0x080, fclass(qNaN) = 0x200
- 참조값은 파이썬 `struct` 로 만들 수 있다: `struct.unpack('<I', struct.pack('<f', v))`

## 상태

개요만 있음. 각 하위 모듈은 착수 시 별도 문서로 상세화한다.
