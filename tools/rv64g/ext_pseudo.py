# -*- coding: utf-8 -*-
"""의사 명령(pseudo-instruction).

각 항목은 두 가지를 가진다.
  - ISA 텍스트용: 피연산자 목록 + 기계어 토큰(고정 레지스터 비트를 직접 박음)
  - 인코더용: expand(ops, ctx) -> 기본 명령 문자열 목록
두 경로가 독립적이라 selftest 에서 서로 대조해 기계어 토큰의 오타를 잡는다.

size == 2 인 항목(8바이트 기계어 줄)은 게임 어셈블러가 32비트를 넘는 줄을 어떻게
다루는지 검증되기 전까지 실험적이다 (README 의 검증 항목 참고).
"""
from dataclasses import dataclass, field
from .formats import PCREL, B_ALIGN, B_RANGE, J_ALIGN, J_RANGE, I12_ASSERT, T32_ASSERT
from .fields import CSR


@dataclass
class Pseudo:
    mnemonic: str
    operands: list                 # [(이름, 종류)]
    mc: list                       # 기계어 토큰
    expand: object                 # (ops: dict[str,str], ctx) -> [str]
    ext: str = 'pseudo'
    desc: str = ''
    virtuals: list = field(default_factory=list)
    asserts: list = field(default_factory=list)
    size: int = 1                  # 32비트 워드 수


def _b(f3, rs2_tok, rs1_tok):
    return ['%o[12]', '%o[10:5]', rs2_tok, rs1_tok, f3, '%o[4:1]', '%o[11]', '1100011']


def _csr12(name):
    return format(CSR[name], '012b')


X0, X1, X6 = '00000', '00001', '00110'

HI = ('h', '(%o + 2048) >> 12', lambda v, pc: ((v['o'] + 2048) >> 12) & 0xFFFFF)
HI_I = ('h', '(%i + 2048) >> 12', lambda v, pc: ((v['i'] + 2048) >> 12) & 0xFFFFF)
# li32 는 S33 타입으로 -2^31..2^32-1 을 모두 받는다. 타입이 허용하는 -2^32..-2^31-1 만 단언문으로 막는다.
LI32_ASSERT = ('%i >= -2147483648', lambda v: -2147483648 <= v['i'] <= 4294967295, 'value out of 32-bit range')
LA_RANGE = ('%o >= -2147483648 && %o <= 2147483647', lambda v: -2147483648 <= v['o'] <= 2147483647, 'target out of +-2 GiB range')


def _hi_lo(off):
    hi = ((off + 0x800) >> 12) & 0xFFFFF
    lo = off & 0xFFF
    if lo >= 0x800:
        lo -= 0x1000
    return hi, lo


PSEUDO = [
    Pseudo('nop', [], ['00000000000000000000000000010011'], lambda o, c: ['addi x0, x0, 0'], desc='addi x0, x0, 0'),
    Pseudo('mv', [('d', 'reg'), ('a', 'reg')], ['000000000000', '%a[4:0]', '000', '%d[4:0]', '0010011'],
           lambda o, c: ['addi %(d)s, %(a)s, 0' % o], desc='rd = rs  (addi rd, rs, 0)'),
    Pseudo('not', [('d', 'reg'), ('a', 'reg')], ['111111111111', '%a[4:0]', '100', '%d[4:0]', '0010011'],
           lambda o, c: ['xori %(d)s, %(a)s, -1' % o], desc='rd = ~rs  (xori rd, rs, -1)'),
    Pseudo('neg', [('d', 'reg'), ('b', 'reg')], ['0100000', '%b[4:0]', X0, '000', '%d[4:0]', '0110011'],
           lambda o, c: ['sub %(d)s, x0, %(b)s' % o], desc='rd = -rs  (sub rd, x0, rs)'),
    Pseudo('negw', [('d', 'reg'), ('b', 'reg')], ['0100000', '%b[4:0]', X0, '000', '%d[4:0]', '0111011'],
           lambda o, c: ['subw %(d)s, x0, %(b)s' % o], desc='rd = sext32(-rs)  (subw rd, x0, rs)'),
    Pseudo('sext.w', [('d', 'reg'), ('a', 'reg')], ['000000000000', '%a[4:0]', '000', '%d[4:0]', '0011011'],
           lambda o, c: ['addiw %(d)s, %(a)s, 0' % o], desc='rd = sext32(rs)  (addiw rd, rs, 0)'),
    Pseudo('seqz', [('d', 'reg'), ('a', 'reg')], ['000000000001', '%a[4:0]', '011', '%d[4:0]', '0010011'],
           lambda o, c: ['sltiu %(d)s, %(a)s, 1' % o], desc='rd = (rs == 0)  (sltiu rd, rs, 1)'),
    Pseudo('snez', [('d', 'reg'), ('b', 'reg')], ['0000000', '%b[4:0]', X0, '011', '%d[4:0]', '0110011'],
           lambda o, c: ['sltu %(d)s, x0, %(b)s' % o], desc='rd = (rs != 0)  (sltu rd, x0, rs)'),
    Pseudo('sltz', [('d', 'reg'), ('a', 'reg')], ['0000000', X0, '%a[4:0]', '010', '%d[4:0]', '0110011'],
           lambda o, c: ['slt %(d)s, %(a)s, x0' % o], desc='rd = (rs < 0)  (slt rd, rs, x0)'),
    Pseudo('sgtz', [('d', 'reg'), ('b', 'reg')], ['0000000', '%b[4:0]', X0, '010', '%d[4:0]', '0110011'],
           lambda o, c: ['slt %(d)s, x0, %(b)s' % o], desc='rd = (rs > 0)  (slt rd, x0, rs)'),
    Pseudo('li', [('d', 'reg'), ('i', 'imm')], ['%i[11:0]', X0, '000', '%d[4:0]', '0010011'],
           lambda o, c: ['addi %(d)s, x0, %(i)s' % o], asserts=[I12_ASSERT],
           desc='rd = imm (12-bit only; use li32 for larger values)'),

    Pseudo('beqz', [('a', 'reg'), ('t', 'target')], _b('000', X0, '%a[4:0]'),
           lambda o, c: ['beq %(a)s, x0, %(t)s' % o], virtuals=PCREL, asserts=[T32_ASSERT, B_ALIGN, B_RANGE], desc='beq rs, x0, target'),
    Pseudo('bnez', [('a', 'reg'), ('t', 'target')], _b('001', X0, '%a[4:0]'),
           lambda o, c: ['bne %(a)s, x0, %(t)s' % o], virtuals=PCREL, asserts=[T32_ASSERT, B_ALIGN, B_RANGE], desc='bne rs, x0, target'),
    Pseudo('blez', [('b', 'reg'), ('t', 'target')], _b('101', '%b[4:0]', X0),
           lambda o, c: ['bge x0, %(b)s, %(t)s' % o], virtuals=PCREL, asserts=[T32_ASSERT, B_ALIGN, B_RANGE], desc='bge x0, rs, target'),
    Pseudo('bgez', [('a', 'reg'), ('t', 'target')], _b('101', X0, '%a[4:0]'),
           lambda o, c: ['bge %(a)s, x0, %(t)s' % o], virtuals=PCREL, asserts=[T32_ASSERT, B_ALIGN, B_RANGE], desc='bge rs, x0, target'),
    Pseudo('bltz', [('a', 'reg'), ('t', 'target')], _b('100', X0, '%a[4:0]'),
           lambda o, c: ['blt %(a)s, x0, %(t)s' % o], virtuals=PCREL, asserts=[T32_ASSERT, B_ALIGN, B_RANGE], desc='blt rs, x0, target'),
    Pseudo('bgtz', [('b', 'reg'), ('t', 'target')], _b('100', '%b[4:0]', X0),
           lambda o, c: ['blt x0, %(b)s, %(t)s' % o], virtuals=PCREL, asserts=[T32_ASSERT, B_ALIGN, B_RANGE], desc='blt x0, rs, target'),
    Pseudo('bgt', [('a', 'reg'), ('b', 'reg'), ('t', 'target')], _b('100', '%a[4:0]', '%b[4:0]'),
           lambda o, c: ['blt %(b)s, %(a)s, %(t)s' % o], virtuals=PCREL, asserts=[T32_ASSERT, B_ALIGN, B_RANGE], desc='blt rs2, rs1, target'),
    Pseudo('ble', [('a', 'reg'), ('b', 'reg'), ('t', 'target')], _b('101', '%a[4:0]', '%b[4:0]'),
           lambda o, c: ['bge %(b)s, %(a)s, %(t)s' % o], virtuals=PCREL, asserts=[T32_ASSERT, B_ALIGN, B_RANGE], desc='bge rs2, rs1, target'),
    Pseudo('bgtu', [('a', 'reg'), ('b', 'reg'), ('t', 'target')], _b('110', '%a[4:0]', '%b[4:0]'),
           lambda o, c: ['bltu %(b)s, %(a)s, %(t)s' % o], virtuals=PCREL, asserts=[T32_ASSERT, B_ALIGN, B_RANGE], desc='bltu rs2, rs1, target'),
    Pseudo('bleu', [('a', 'reg'), ('b', 'reg'), ('t', 'target')], _b('111', '%a[4:0]', '%b[4:0]'),
           lambda o, c: ['bgeu %(b)s, %(a)s, %(t)s' % o], virtuals=PCREL, asserts=[T32_ASSERT, B_ALIGN, B_RANGE], desc='bgeu rs2, rs1, target'),

    Pseudo('j', [('t', 'target')], ['%o[20]', '%o[10:1]', '%o[11]', '%o[19:12]', X0, '1101111'],
           lambda o, c: ['jal x0, %(t)s' % o], virtuals=PCREL, asserts=[T32_ASSERT, J_ALIGN, J_RANGE], desc='jal x0, target'),
    Pseudo('jal', [('t', 'target')], ['%o[20]', '%o[10:1]', '%o[11]', '%o[19:12]', X1, '1101111'],
           lambda o, c: ['jal x1, %(t)s' % o], virtuals=PCREL, asserts=[T32_ASSERT, J_ALIGN, J_RANGE], desc='jal x1, target'),
    Pseudo('jr', [('a', 'reg')], ['000000000000', '%a[4:0]', '000', X0, '1100111'],
           lambda o, c: ['jalr x0, 0(%(a)s)' % o], desc='jalr x0, 0(rs)'),
    Pseudo('jalr', [('a', 'reg')], ['000000000000', '%a[4:0]', '000', X1, '1100111'],
           lambda o, c: ['jalr x1, 0(%(a)s)' % o], desc='jalr x1, 0(rs)'),
    Pseudo('ret', [], ['00000000000000001000000001100111'], lambda o, c: ['jalr x0, 0(x1)'], desc='jalr x0, 0(x1)'),

    Pseudo('csrr', [('d', 'reg'), ('n', 'csr')], ['%n[11:0]', X0, '010', '%d[4:0]', '1110011'],
           lambda o, c: ['csrrs %(d)s, %(n)s, x0' % o], desc='csrrs rd, csr, x0'),
    Pseudo('csrw', [('n', 'csr'), ('a', 'reg')], ['%n[11:0]', '%a[4:0]', '001', X0, '1110011'],
           lambda o, c: ['csrrw x0, %(n)s, %(a)s' % o], desc='csrrw x0, csr, rs'),
    Pseudo('csrs', [('n', 'csr'), ('a', 'reg')], ['%n[11:0]', '%a[4:0]', '010', X0, '1110011'],
           lambda o, c: ['csrrs x0, %(n)s, %(a)s' % o], desc='csrrs x0, csr, rs'),
    Pseudo('csrc', [('n', 'csr'), ('a', 'reg')], ['%n[11:0]', '%a[4:0]', '011', X0, '1110011'],
           lambda o, c: ['csrrc x0, %(n)s, %(a)s' % o], desc='csrrc x0, csr, rs'),
    Pseudo('csrwi', [('n', 'csr'), ('z', 'zimm')], ['%n[11:0]', '%z[4:0]', '101', X0, '1110011'],
           lambda o, c: ['csrrwi x0, %(n)s, %(z)s' % o], desc='csrrwi x0, csr, zimm'),
    Pseudo('csrsi', [('n', 'csr'), ('z', 'zimm')], ['%n[11:0]', '%z[4:0]', '110', X0, '1110011'],
           lambda o, c: ['csrrsi x0, %(n)s, %(z)s' % o], desc='csrrsi x0, csr, zimm'),
    Pseudo('csrci', [('n', 'csr'), ('z', 'zimm')], ['%n[11:0]', '%z[4:0]', '111', X0, '1110011'],
           lambda o, c: ['csrrci x0, %(n)s, %(z)s' % o], desc='csrrci x0, csr, zimm'),
    Pseudo('rdcycle', [('d', 'reg')], [_csr12('cycle'), X0, '010', '%d[4:0]', '1110011'],
           lambda o, c: ['csrrs %(d)s, cycle, x0' % o], desc='csrrs rd, cycle, x0'),
    Pseudo('rdtime', [('d', 'reg')], [_csr12('time'), X0, '010', '%d[4:0]', '1110011'],
           lambda o, c: ['csrrs %(d)s, time, x0' % o], desc='csrrs rd, time, x0'),
    Pseudo('rdinstret', [('d', 'reg')], [_csr12('instret'), X0, '010', '%d[4:0]', '1110011'],
           lambda o, c: ['csrrs %(d)s, instret, x0' % o], desc='csrrs rd, instret, x0'),
    Pseudo('frcsr', [('d', 'reg')], [_csr12('fcsr'), X0, '010', '%d[4:0]', '1110011'],
           lambda o, c: ['csrrs %(d)s, fcsr, x0' % o], desc='csrrs rd, fcsr, x0'),
    Pseudo('fscsr', [('a', 'reg')], [_csr12('fcsr'), '%a[4:0]', '001', X0, '1110011'],
           lambda o, c: ['csrrw x0, fcsr, %(a)s' % o], desc='csrrw x0, fcsr, rs'),
    Pseudo('frrm', [('d', 'reg')], [_csr12('frm'), X0, '010', '%d[4:0]', '1110011'],
           lambda o, c: ['csrrs %(d)s, frm, x0' % o], desc='csrrs rd, frm, x0'),
    Pseudo('fsrm', [('a', 'reg')], [_csr12('frm'), '%a[4:0]', '001', X0, '1110011'],
           lambda o, c: ['csrrw x0, frm, %(a)s' % o], desc='csrrw x0, frm, rs'),
    Pseudo('frflags', [('d', 'reg')], [_csr12('fflags'), X0, '010', '%d[4:0]', '1110011'],
           lambda o, c: ['csrrs %(d)s, fflags, x0' % o], desc='csrrs rd, fflags, x0'),
    Pseudo('fsflags', [('a', 'reg')], [_csr12('fflags'), '%a[4:0]', '001', X0, '1110011'],
           lambda o, c: ['csrrw x0, fflags, %(a)s' % o], desc='csrrw x0, fflags, rs'),

    # 같은 피연산자를 rs1, rs2 두 자리에 쓰는 형태. 게임 어셈블러가 %a[4:0] 를 두 번 받아 주는지 검증 항목.
    Pseudo('fmv.s', [('d', 'freg'), ('a', 'freg')], ['0010000', '%a[4:0]', '%a[4:0]', '000', '%d[4:0]', '1010011'],
           lambda o, c: ['fsgnj.s %(d)s, %(a)s, %(a)s' % o], desc='fsgnj.s rd, rs, rs'),
    Pseudo('fneg.s', [('d', 'freg'), ('a', 'freg')], ['0010000', '%a[4:0]', '%a[4:0]', '001', '%d[4:0]', '1010011'],
           lambda o, c: ['fsgnjn.s %(d)s, %(a)s, %(a)s' % o], desc='fsgnjn.s rd, rs, rs'),
    Pseudo('fabs.s', [('d', 'freg'), ('a', 'freg')], ['0010000', '%a[4:0]', '%a[4:0]', '010', '%d[4:0]', '1010011'],
           lambda o, c: ['fsgnjx.s %(d)s, %(a)s, %(a)s' % o], desc='fsgnjx.s rd, rs, rs'),
    Pseudo('fmv.d', [('d', 'freg'), ('a', 'freg')], ['0010001', '%a[4:0]', '%a[4:0]', '000', '%d[4:0]', '1010011'],
           lambda o, c: ['fsgnj.d %(d)s, %(a)s, %(a)s' % o], desc='fsgnj.d rd, rs, rs'),
    Pseudo('fneg.d', [('d', 'freg'), ('a', 'freg')], ['0010001', '%a[4:0]', '%a[4:0]', '001', '%d[4:0]', '1010011'],
           lambda o, c: ['fsgnjn.d %(d)s, %(a)s, %(a)s' % o], desc='fsgnjn.d rd, rs, rs'),
    Pseudo('fabs.d', [('d', 'freg'), ('a', 'freg')], ['0010001', '%a[4:0]', '%a[4:0]', '010', '%d[4:0]', '1010011'],
           lambda o, c: ['fsgnjx.d %(d)s, %(a)s, %(a)s' % o], desc='fsgnjx.d rd, rs, rs'),
]

# --- 8바이트(2명령) 의사 명령: 실험적 ---------------------------------------


def _expand_li32(o, c):
    hi, lo = _hi_lo(c.imm(o['i']))
    return ['lui %s, %d' % (o['d'], hi), 'addiw %s, %s, %d' % (o['d'], o['d'], lo)]


def _expand_la(o, c):
    hi, lo = _hi_lo(c.target(o['t']) - c.pc)
    return ['auipc %s, %d' % (o['d'], hi), 'addi %s, %s, %d' % (o['d'], o['d'], lo)]


def _expand_call(o, c):
    hi, lo = _hi_lo(c.target(o['t']) - c.pc)
    return ['auipc x1, %d' % hi, 'jalr x1, %d(x1)' % lo]


def _expand_tail(o, c):
    hi, lo = _hi_lo(c.target(o['t']) - c.pc)
    return ['auipc x6, %d' % hi, 'jalr x0, %d(x6)' % lo]


PSEUDO_EXPERIMENTAL = [
    Pseudo('li32', [('d', 'reg'), ('i', 'imm32')],
           ['%h[19:0]', '%d[4:0]', '0110111', '%i[11:0]', '%d[4:0]', '000', '%d[4:0]', '0011011'],
           _expand_li32, virtuals=[HI_I], asserts=[LI32_ASSERT], size=2, ext='pseudo(2)',
           desc='rd = sext32(imm)  (lui rd, hi; addiw rd, rd, lo)  EXPERIMENTAL 8-byte line'),
    Pseudo('la', [('d', 'reg'), ('t', 'target')],
           ['%h[19:0]', '%d[4:0]', '0010111', '%o[11:0]', '%d[4:0]', '000', '%d[4:0]', '0010011'],
           _expand_la, virtuals=PCREL + [HI], asserts=[T32_ASSERT, LA_RANGE], size=2, ext='pseudo(2)',
           desc='rd = address of target  (auipc rd, hi; addi rd, rd, lo)  EXPERIMENTAL'),
    Pseudo('call', [('t', 'target')],
           ['%h[19:0]', X1, '0010111', '%o[11:0]', X1, '000', X1, '1100111'],
           _expand_call, virtuals=PCREL + [HI], asserts=[T32_ASSERT, LA_RANGE], size=2, ext='pseudo(2)',
           desc='x1 = pc + 8; pc = target  (auipc x1, hi; jalr x1, lo(x1))  EXPERIMENTAL'),
    Pseudo('tail', [('t', 'target')],
           ['%h[19:0]', X6, '0010111', '%o[11:0]', X6, '000', X0, '1100111'],
           _expand_tail, virtuals=PCREL + [HI], asserts=[T32_ASSERT, LA_RANGE], size=2, ext='pseudo(2)',
           desc='pc = target via x6  (auipc x6, hi; jalr x0, lo(x6))  EXPERIMENTAL'),
]

ALL = PSEUDO + PSEUDO_EXPERIMENTAL
BY_NAME = {}
for p in ALL:
    BY_NAME.setdefault(p.mnemonic, []).append(p)
