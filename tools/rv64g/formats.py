# -*- coding: utf-8 -*-
"""명령 형식 정의.

하나의 표(Instr)에서 두 가지를 만든다.
  1. 게임 어셈블러용 .isa 정의 텍스트 (render_isa)
  2. 파이썬 참조 인코더용 32비트 기계어 (encode)

기계어 줄은 왼쪽이 MSB(bit 31)다. 피연산자는 항상 비트 슬라이싱(%d[4:0])으로 적는다.
게임 어셈블러의 한 글자 방식은 피연산자 이름의 첫 글자만 보기 때문에 rd/rs1/rs2 처럼
첫 글자가 겹치는 이름을 쓸 수 없다. 그래서 피연산자 이름은 전부 한 글자다:
  %d rd   %a rs1   %b rs2   %c rs3   %i 즉시값   %t 분기 대상   %o 오프셋(가상)
  %s 시프트량   %n CSR 번호   %z CSR 즉시값   %r 반올림 모드

즉시값 피연산자에는 게임이 크기 타입을 요구한다. 게임 실행 파일의 어셈블러 오류 문구:
  "Immediate operand must have size constraint, e.g. %a:U8(immediate)."
  "Expected an U for unsigned or S for signed here"
  "Operand value outside of {n}-bit signed range"
종류별 타입은 TYPE_OF 에 있다. 타입이 대신 검사하는 범위 단언문은 expr 를 None 으로 두어
.isa 에는 내지 않고 파이썬 참조 인코더만 쓴다.
"""
from dataclasses import dataclass

OP = {
    'LOAD': 0b0000011, 'LOAD_FP': 0b0000111, 'MISC_MEM': 0b0001111, 'OP_IMM': 0b0010011,
    'AUIPC': 0b0010111, 'OP_IMM_32': 0b0011011, 'STORE': 0b0100011, 'STORE_FP': 0b0100111,
    'AMO': 0b0101111, 'OP': 0b0110011, 'LUI': 0b0110111, 'OP_32': 0b0111011,
    'MADD': 0b1000011, 'MSUB': 0b1000111, 'NMSUB': 0b1001011, 'NMADD': 0b1001111,
    'OP_FP': 0b1010011, 'BRANCH': 0b1100011, 'JALR': 0b1100111, 'JAL': 0b1101111,
    'SYSTEM': 0b1110011,
}


@dataclass
class Instr:
    mnemonic: str
    fmt: str                 # 아래 FORMATS 의 키
    opcode: int
    funct3: int = None
    funct7: int = None       # SH6 에서는 funct6, AMO/LR 에서는 funct5
    rs2: int = None          # rs2 자리가 고정인 명령 (fsqrt, fcvt, fmv, lr)
    regs: tuple = None       # 피연산자 레지스터 종류 (FR2/FR3 에서 사용) 예: ('reg', 'freg')
    rm: bool = False         # 반올림 모드 피연산자 유무
    aqrl: int = 0            # AMO: aq<<1 | rl
    ext: str = 'I'
    desc: str = ''


def bits(v, n):
    return format(v & ((1 << n) - 1), '0%db' % n)


# ---------------------------------------------------------------------------
# 형식별 정의: 문법 피연산자 목록, 기계어 토큰, 가상 피연산자, 단언문
#
# 문법 피연산자: (이름, 종류)  종류 = reg | freg | mem | mem0 | rm | imm | imm20 | imm32 | sh6 | sh5 | zimm | csr | target
# 기계어 토큰: 리터럴 비트 문자열 또는 '%x[hi:lo]'
# ---------------------------------------------------------------------------

# expr 가 None 인 단언문은 피연산자 타입(S12, U20, …)이 대신 검사하므로 .isa 에 내지 않는다.
I12_ASSERT = (None, lambda v: -2048 <= v['i'] <= 2047, 'immediate out of 12-bit signed range')
U20_ASSERT = (None, lambda v: 0 <= v['i'] <= 1048575, 'immediate out of 20-bit unsigned range')
SH6_ASSERT = (None, lambda v: 0 <= v['s'] <= 63, 'shift amount must be 0..63')
SH5_ASSERT = (None, lambda v: 0 <= v['s'] <= 31, 'shift amount must be 0..31')
CSR_ASSERT = (None, lambda v: 0 <= v['n'] <= 4095, 'csr number must be 0..4095')
ZIMM_ASSERT = (None, lambda v: 0 <= v['z'] <= 31, 'csr immediate must be 0..31')
T32_ASSERT = (None, lambda v: 0 <= v['t'] <= 4294967295, 'target must be a 32-bit unsigned address')
B_ALIGN = ('%o % 2 == 0', lambda v: v['o'] % 2 == 0, 'branch target must be 2-byte aligned')
B_RANGE = ('%o >= -4096 && %o <= 4094', lambda v: -4096 <= v['o'] <= 4094, 'branch target out of range (+-4 KiB)')
J_ALIGN = ('%o % 2 == 0', lambda v: v['o'] % 2 == 0, 'jump target must be 2-byte aligned')
J_RANGE = ('%o >= -1048576 && %o <= 1048574', lambda v: -1048576 <= v['o'] <= 1048574, 'jump target out of range (+-1 MiB)')

PCREL = [('o', '%t - $start', lambda v, pc: v['t'] - pc)]


def _rm_tokens(instr, with_rm):
    return '%r[2:0]' if with_rm else '111'


def definitions(instr):
    """Instr -> [(operands, virtuals, asserts, mc_tokens)] (반올림 모드 유무로 2개가 될 수 있음)."""
    f = instr
    f3 = bits(f.funct3, 3) if f.funct3 is not None else None
    op = bits(f.opcode, 7)
    fmt = f.fmt
    if fmt == 'R':
        return [([('d', 'reg'), ('a', 'reg'), ('b', 'reg')], [], [],
                 [bits(f.funct7, 7), '%b[4:0]', '%a[4:0]', f3, '%d[4:0]', op])]
    if fmt == 'I':
        return [([('d', 'reg'), ('a', 'reg'), ('i', 'imm')], [], [I12_ASSERT],
                 ['%i[11:0]', '%a[4:0]', f3, '%d[4:0]', op])]
    if fmt == 'IL':      # rd, imm(rs1)
        return [([('d', 'reg'), ('i', 'imm'), ('a', 'mem')], [], [I12_ASSERT],
                 ['%i[11:0]', '%a[4:0]', f3, '%d[4:0]', op])]
    if fmt == 'FL':
        return [([('d', 'freg'), ('i', 'imm'), ('a', 'mem')], [], [I12_ASSERT],
                 ['%i[11:0]', '%a[4:0]', f3, '%d[4:0]', op])]
    if fmt == 'S':
        return [([('b', 'reg'), ('i', 'imm'), ('a', 'mem')], [], [I12_ASSERT],
                 ['%i[11:5]', '%b[4:0]', '%a[4:0]', f3, '%i[4:0]', op])]
    if fmt == 'FS':
        return [([('b', 'freg'), ('i', 'imm'), ('a', 'mem')], [], [I12_ASSERT],
                 ['%i[11:5]', '%b[4:0]', '%a[4:0]', f3, '%i[4:0]', op])]
    if fmt == 'B':
        return [([('a', 'reg'), ('b', 'reg'), ('t', 'target')], PCREL, [T32_ASSERT, B_ALIGN, B_RANGE],
                 ['%o[12]', '%o[10:5]', '%b[4:0]', '%a[4:0]', f3, '%o[4:1]', '%o[11]', op])]
    if fmt == 'U':
        return [([('d', 'reg'), ('i', 'imm20')], [], [U20_ASSERT],
                 ['%i[19:0]', '%d[4:0]', op])]
    if fmt == 'J':
        return [([('d', 'reg'), ('t', 'target')], PCREL, [T32_ASSERT, J_ALIGN, J_RANGE],
                 ['%o[20]', '%o[10:1]', '%o[11]', '%o[19:12]', '%d[4:0]', op])]
    if fmt == 'SH6':
        return [([('d', 'reg'), ('a', 'reg'), ('s', 'sh6')], [], [SH6_ASSERT],
                 [bits(f.funct7, 6), '%s[5:0]', '%a[4:0]', f3, '%d[4:0]', op])]
    if fmt == 'SH5':
        return [([('d', 'reg'), ('a', 'reg'), ('s', 'sh5')], [], [SH5_ASSERT],
                 [bits(f.funct7, 7), '%s[4:0]', '%a[4:0]', f3, '%d[4:0]', op])]
    if fmt == 'CSR':
        return [([('d', 'reg'), ('n', 'csr'), ('a', 'reg')], [], [CSR_ASSERT],
                 ['%n[11:0]', '%a[4:0]', f3, '%d[4:0]', op])]
    if fmt == 'CSRI':
        return [([('d', 'reg'), ('n', 'csr'), ('z', 'zimm')], [], [CSR_ASSERT, ZIMM_ASSERT],
                 ['%n[11:0]', '%z[4:0]', f3, '%d[4:0]', op])]
    if fmt == 'FIX':     # 피연산자 없음, funct7 자리에 32비트 워드 전체
        return [([], [], [], [bits(f.funct7, 32)])]
    if fmt == 'AMO':     # rd, rs2, (rs1)
        return [([('d', 'reg'), ('b', 'reg'), ('a', 'mem0')], [], [],
                 [bits(f.funct7, 5), bits(f.aqrl, 2), '%b[4:0]', '%a[4:0]', f3, '%d[4:0]', op])]
    if fmt == 'LR':      # rd, (rs1)
        return [([('d', 'reg'), ('a', 'mem0')], [], [],
                 [bits(f.funct7, 5), bits(f.aqrl, 2), '00000', '%a[4:0]', f3, '%d[4:0]', op])]
    if fmt == 'FR':      # rd, rs1, rs2 [, rm]
        base = [('d', 'freg'), ('a', 'freg'), ('b', 'freg')]
        out = []
        for with_rm in (True, False):
            ops = base + ([('r', 'rm')] if with_rm else [])
            out.append((ops, [], [], [bits(f.funct7, 7), '%b[4:0]', '%a[4:0]', _rm_tokens(f, with_rm), '%d[4:0]', op]))
        return out
    if fmt == 'FR2':     # rd, rs1 [, rm]  (rs2 고정)
        rd_k, a_k = f.regs
        out = []
        for with_rm in (True, False):
            ops = [('d', rd_k), ('a', a_k)] + ([('r', 'rm')] if with_rm else [])
            out.append((ops, [], [], [bits(f.funct7, 7), bits(f.rs2, 5), '%a[4:0]', _rm_tokens(f, with_rm), '%d[4:0]', op]))
        return out
    if fmt == 'FR3':     # funct3 고정, rm 없음. regs 가 2개면 rs2 고정, 3개면 rs2 피연산자
        if len(f.regs) == 3:
            rd_k, a_k, b_k = f.regs
            return [([('d', rd_k), ('a', a_k), ('b', b_k)], [], [],
                     [bits(f.funct7, 7), '%b[4:0]', '%a[4:0]', f3, '%d[4:0]', op])]
        rd_k, a_k = f.regs
        return [([('d', rd_k), ('a', a_k)], [], [],
                 [bits(f.funct7, 7), bits(f.rs2, 5), '%a[4:0]', f3, '%d[4:0]', op])]
    if fmt == 'R4':      # rd, rs1, rs2, rs3 [, rm]   funct7 자리에는 fmt(2비트)만 사용
        base = [('d', 'freg'), ('a', 'freg'), ('b', 'freg'), ('c', 'freg')]
        out = []
        for with_rm in (True, False):
            ops = base + ([('r', 'rm')] if with_rm else [])
            out.append((ops, [], [], ['%c[4:0]', bits(f.funct7, 2), '%b[4:0]', '%a[4:0]', _rm_tokens(f, with_rm), '%d[4:0]', op]))
        return out
    raise ValueError('unknown format %s for %s' % (fmt, f.mnemonic))


# ---------------------------------------------------------------------------
# .isa 텍스트
# ---------------------------------------------------------------------------

def isa_token(tok):
    """기계어 토큰을 게임 문법으로. 게임 파서는 슬라이스에 항상 콜론을 요구하므로 %o[20] 은 %o[20:20] 으로 쓴다
    (게임 오류: "Expected slice syntax after field/pattern reference in bit pattern", 2026-09-15 A1 에서 확인)."""
    if tok.startswith('%') and '[' in tok and ':' not in tok:
        n = tok[tok.index('[') + 1:-1]
        return '%s[%s:%s]' % (tok[:tok.index('[')], n, n)
    return tok


FIELD_OF = {'reg': 'reg', 'freg': 'freg', 'rm': 'rm',
            'imm': 'immediate', 'imm20': 'immediate', 'imm32': 'immediate',
            'sh6': 'immediate', 'sh5': 'immediate', 'zimm': 'immediate',
            'target': 'immediate | label', 'csr': 'csr | immediate'}

# 즉시값 종류별 크기 타입 (S = 부호 있음, U = 없음). 게임 어셈블러가 즉시값마다 요구한다.
#   imm    I/S형 12비트      imm20  lui/auipc 상위 20비트 (0..0xFFFFF)
#   sh6    64비트 시프트량    sh5    W형 시프트량    zimm  CSR 즉시값    csr  CSR 번호
#   target 절대 주소(label)  imm32  li32 (S33: -2^31..2^32-1 을 한 타입으로 받기 위해)
TYPE_OF = {'imm': 'S12', 'imm20': 'U20', 'imm32': 'S33', 'sh6': 'U6', 'sh5': 'U5',
           'zimm': 'U5', 'csr': 'U12', 'target': 'U32'}


def syntax_line(mnemonic, operands):
    """문법 줄. 메모리 피연산자는 RISC-V 관례대로 imm(rs1) 로 적고, 즉시값에는 크기 타입을 붙인다."""
    parts = []
    i = 0
    while i < len(operands):
        name, kind = operands[i]
        if kind == 'mem':                 # 직전 피연산자가 즉시값이고 그 뒤에 (rs1) 이 붙는다
            parts[-1] = parts[-1] + ' (%%%s(reg))' % name
        elif kind == 'mem0':
            parts.append('(%%%s(reg))' % name)
        else:
            t = TYPE_OF.get(kind)
            parts.append('%%%s%s(%s)' % (name, ':' + t if t else '', FIELD_OF[kind]))
        i += 1
    return mnemonic if not parts else mnemonic + ' ' + ', '.join(parts)


def render_isa(instr):
    """하나의 Instr 를 .isa 정의 블록(들)로 만든다."""
    blocks = []
    for operands, virtuals, asserts, mc in definitions(instr):
        lines = [syntax_line(instr.mnemonic, operands)]
        for name, expr, _ in virtuals:
            lines.append('%%%s = %s' % (name, expr))
        for expr, _, msg in asserts:
            if expr is None:          # 타입이 대신 검사
                continue
            lines.append('assert(%s, "%s: %s")' % (expr, instr.mnemonic, msg))
        lines.append(' '.join(isa_token(t) for t in mc))
        lines.append('# [%s] %s' % (instr.ext, instr.desc or instr.mnemonic))
        blocks.append('\n'.join(lines))
    return '\n\n'.join(blocks)


# ---------------------------------------------------------------------------
# 인코딩
# ---------------------------------------------------------------------------

def encode_tokens(mc, values):
    """기계어 토큰 목록과 피연산자 값으로 정수를 만든다 (왼쪽이 MSB)."""
    word = 0
    nbits = 0
    for tok in mc:
        if tok[0] in '01':
            word = (word << len(tok)) | int(tok, 2)
            nbits += len(tok)
            continue
        name = tok[1]
        hi, lo = tok[tok.index('[') + 1:-1].split(':') if ':' in tok else (tok[tok.index('[') + 1:-1],) * 2
        hi, lo = int(hi), int(lo)
        v = values[name]
        width = hi - lo + 1
        word = (word << width) | ((v >> lo) & ((1 << width) - 1))
        nbits += width
    assert nbits % 32 == 0, 'machine code is %d bits' % nbits
    return word, nbits


def encode(instr, operands_present, values, pc):
    """values: 피연산자 이름 -> 정수. operands_present: 실제로 주어진 피연산자 이름 집합."""
    for operands, virtuals, asserts, mc in definitions(instr):
        names = {n for n, _ in operands}
        if names != operands_present:
            continue
        vals = dict(values)
        for name, _, fn in virtuals:
            vals[name] = fn(vals, pc)
        for _, fn, msg in asserts:
            if not fn(vals):
                raise ValueError('%s: %s' % (instr.mnemonic, msg))
        return encode_tokens(mc, vals)
    raise ValueError('%s: operand set %s does not match any form' % (instr.mnemonic, sorted(operands_present)))
