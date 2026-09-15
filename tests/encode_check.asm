# 게임 어셈블러 검증 프로그램.
# tools/rv_encode.py 로 만든 tests/encode_check.expected.txt 의 바이트 열과
# 게임이 만든 기계어를 줄 단위로 대조한다. 형식마다 최소 한 명령, 음수 즉시값,
# 앞/뒤 분기, 의사 명령, 8바이트 의사 명령(실험)을 포함한다.

start:
    addi  x1, x0, 5           # I형, 양수
    addi  x2, x0, -1          # I형, 음수 (부호 즉시값 검증)
    lui   x3, 0x12345         # U형
    auipc x4, 1               # U형, PC 상대는 하드웨어가 처리
    add   x5, x1, x2          # R형
    sub   x5, x1, x2
    slli  x6, x1, 63          # 6비트 shamt
    srai  x6, x2, 1
    sraiw x7, x2, 5           # 5비트 shamt, funct7
    addiw x8, x1, -3
    sraw  x9, x2, x1
    lw    x10, -8(x1)         # 로드, 음수 오프셋
    ld    x11, 0(x2)
    sd    x11, 16(x3)         # 스토어
    sb    x1, -1(x2)
loop:
    beq   x1, x2, loop        # 뒤로 분기 (오프셋 0)
    bne   x1, x2, forward     # 앞으로 분기
    bltu  x1, x2, start       # 뒤로 분기, 음수 오프셋
    jal   x0, forward         # J형
    jalr  x0, 0(x1)           # jalr, 메모리 문법
    jalr  x1, x2, 4           # jalr, 레지스터 우선 문법
forward:
    mul   x12, x1, x2         # M
    mulhu x12, x1, x2
    divw  x12, x1, x2
    remu  x12, x1, x2
    amoadd.w   x13, x1, (x2)  # A
    amoswap.d.aqrl x13, x1, (x2)
    lr.w  x14, (x2)
    sc.d  x14, x1, (x2)
    csrrs x15, mstatus, x0    # Zicsr, 이름 CSR
    csrrwi x0, 0x305, 3       # Zicsr, 번호 CSR + 즉시값
    fence
    fence.i
    ecall
    ebreak
    fld   f1, 8(x2)           # F/D
    fsw   f3, -4(x4)
    fadd.d f1, f2, f3         # 반올림 모드 생략 (dyn)
    fadd.s f1, f2, f3, rne    # 반올림 모드 명시
    fsqrt.d f4, f5
    fcvt.w.s x1, f2
    fcvt.d.s f1, f2
    fmv.x.d x3, f4
    feq.d  x1, f2, f3
    fmadd.s f1, f2, f3, f4
    # 의사 명령
    nop
    mv    x1, x2
    not   x1, x2
    neg   x1, x2
    li    x1, -100
    beqz  x1, start
    bgt   x1, x2, forward
    j     start
    ret
    csrr  x1, cycle
    rdtime x2
    fmv.d f1, f2              # 같은 피연산자를 두 자리에 (검증 항목)
    fneg.s f1, f2
    # 8바이트 의사 명령 (실험) — 게임이 32비트 넘는 줄을 어떻게 다루는지 확인
    li32  x1, 0x12345678
    li32  x2, -1
    la    x3, start
    call  forward
    tail  start
