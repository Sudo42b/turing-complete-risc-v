# -*- coding: utf-8 -*-
"""참조 어셈블러(인코더).

게임 어셈블러와 독립적으로 같은 표에서 기계어를 만든다. 게임에 넣은 ISA 가 맞게 동작하는지
대조하는 용도이므로 기능은 최소한이다:
  - 레이블 (`name:`), 주석 (# ; //), 빈 줄
  - 기본 명령 전부 + ext_pseudo 의 의사 명령 (기본 명령으로 전개)
  - 즉시값: 10진, 16진(0x), 2진(0b), 음수
  - 메모리 피연산자: imm(reg), (reg)
  - 분기/점프 대상: 레이블 또는 절대 주소(숫자)
지시어(.word 등)는 지원하지 않는다.
"""
import re
from dataclasses import dataclass

from . import BASE_BY_NAME, PSEUDO_BY_NAME
from .fields import XREG_BY_NAME, FREG_BY_NAME, CSR, RM
from .formats import definitions, encode_tokens

COMMENT_RE = re.compile(r'(#|;|//).*$')
LABEL_RE = re.compile(r'^\s*([A-Za-z_.$][\w.$]*)\s*:\s*(.*)$')
MEM_RE = re.compile(r'^\s*([^()\s]*)\s*\(\s*([^()\s]+)\s*\)\s*$')


class AsmError(Exception):
    pass


@dataclass
class Line:
    addr: int
    source: str
    expanded: list      # 기본 명령 문자열들
    words: list         # 32비트 정수들


def parse_int(text):
    t = text.strip().replace('_', '')
    neg = t.startswith('-')
    if neg or t.startswith('+'):
        t = t[1:]
    if t.lower().startswith('0x'):
        v = int(t, 16)
    elif t.lower().startswith('0b'):
        v = int(t, 2)
    elif t.isdigit():
        v = int(t, 10)
    else:
        raise AsmError('bad number: %r' % text)
    return -v if neg else v


def split_operands(text):
    """쉼표로 나누되 괄호 안의 쉼표는 보호한다."""
    out, depth, cur = [], 0, ''
    for ch in text:
        if ch == '(':
            depth += 1
        elif ch == ')':
            depth -= 1
        if ch == ',' and depth == 0:
            out.append(cur.strip())
            cur = ''
        else:
            cur += ch
    if cur.strip():
        out.append(cur.strip())
    return out


class Context:
    def __init__(self, labels, pc):
        self.labels, self.pc = labels, pc

    def target(self, text):
        t = text.strip()
        if t in self.labels:
            return self.labels[t]
        return parse_int(t)

    def imm(self, text):
        return parse_int(text)


def _reg(text, table, what):
    t = text.strip()
    if t not in table:
        raise AsmError('unknown %s register: %r' % (what, text))
    return table[t]


def _slots(operands):
    """정의의 피연산자 목록을 텍스트 피연산자 슬롯으로 묶는다: [(kinds…)]"""
    slots = []
    for name, kind in operands:
        if kind == 'mem':
            slots[-1] = slots[-1] + [(name, kind)]
        elif kind == 'mem0':
            slots.append([(name, kind)])
        else:
            slots.append([(name, kind)])
    return slots


def _values_for(operands, texts, ctx):
    slots = _slots(operands)
    if len(slots) != len(texts):
        return None
    values = {}
    for slot, text in zip(slots, texts):
        if len(slot) == 2:                       # imm(reg)
            (iname, _), (aname, _) = slot
            m = MEM_RE.match(text)
            if not m:
                raise AsmError('expected imm(reg): %r' % text)
            values[iname] = parse_int(m.group(1)) if m.group(1) else 0
            values[aname] = _reg(m.group(2), XREG_BY_NAME, 'integer')
            continue
        name, kind = slot[0]
        if kind == 'mem0':
            m = MEM_RE.match(text)
            if not m or m.group(1):
                raise AsmError('expected (reg): %r' % text)
            values[name] = _reg(m.group(2), XREG_BY_NAME, 'integer')
        elif kind == 'reg':
            values[name] = _reg(text, XREG_BY_NAME, 'integer')
        elif kind == 'freg':
            values[name] = _reg(text, FREG_BY_NAME, 'float')
        elif kind in ('imm', 'imm20', 'imm32', 'sh6', 'sh5', 'zimm'):
            values[name] = parse_int(text)
        elif kind == 'csr':
            values[name] = CSR[text.strip()] if text.strip() in CSR else parse_int(text)
        elif kind == 'rm':
            if text.strip() not in RM:
                raise AsmError('unknown rounding mode: %r' % text)
            values[name] = RM[text.strip()]
        elif kind == 'target':
            values[name] = ctx.target(text)
        else:
            raise AsmError('unhandled operand kind %s' % kind)
    return values


def encode_base(mnemonic, texts, ctx):
    """기본 명령 하나를 32비트 정수로."""
    if mnemonic not in BASE_BY_NAME:
        raise AsmError('unknown instruction: %s' % mnemonic)
    last_err = None
    for instr in BASE_BY_NAME[mnemonic]:
        for operands, virtuals, asserts, mc in definitions(instr):
            try:
                values = _values_for(operands, texts, ctx)
            except AsmError as e:
                last_err = e
                continue
            if values is None:
                continue
            for name, _, fn in virtuals:
                values[name] = fn(values, ctx.pc)
            for _, fn, msg in asserts:
                if not fn(values):
                    raise AsmError('%s: %s' % (mnemonic, msg))
            word, nbits = encode_tokens(mc, values)
            assert nbits == 32
            return word
    raise AsmError('%s: no matching operand form for %r%s' % (mnemonic, texts, ' (%s)' % last_err if last_err else ''))


def _pseudo_size(mnemonic, texts):
    for p in PSEUDO_BY_NAME.get(mnemonic, []):
        if len(_slots(p.operands)) == len(texts):
            return p
    return None


def _is_base(mnemonic, texts):
    """기본 명령 정의 중 텍스트 피연산자 개수가 맞는 것이 있으면 True."""
    for instr in BASE_BY_NAME.get(mnemonic, []):
        for operands, _, _, _ in definitions(instr):
            if len(_slots(operands)) == len(texts):
                return True
    return False


def _split_line(text):
    text = COMMENT_RE.sub('', text).strip()
    if not text:
        return None, None
    parts = text.split(None, 1)
    mnemonic = parts[0].lower()
    texts = split_operands(parts[1]) if len(parts) > 1 else []
    return mnemonic, texts


def assemble(source, origin=0):
    """소스 전체 -> [Line]. 두 번 훑는다 (레이블 주소, 인코딩)."""
    items = []          # (label 또는 None, mnemonic, texts, source)
    for raw in source.splitlines():
        line = COMMENT_RE.sub('', raw).rstrip()
        if not line.strip():
            continue
        m = LABEL_RE.match(line)
        label = None
        if m and not m.group(1).lower() in BASE_BY_NAME and m.group(1).lower() not in PSEUDO_BY_NAME:
            label, line = m.group(1), m.group(2)
        mnemonic, texts = _split_line(line) if line.strip() else (None, None)
        items.append((label, mnemonic, texts, raw.strip()))

    labels, pc = {}, origin
    for label, mnemonic, texts, _ in items:
        if label:
            labels[label] = pc
        if mnemonic is None:
            continue
        if _is_base(mnemonic, texts):
            pc += 4
        else:
            p = _pseudo_size(mnemonic, texts)
            if p is None:
                raise AsmError('unknown instruction: %s' % mnemonic)
            pc += 4 * p.size

    out, pc = [], origin
    for label, mnemonic, texts, src in items:
        if mnemonic is None:
            continue
        ctx = Context(labels, pc)
        if _is_base(mnemonic, texts):
            expanded = [src]
            words = [encode_base(mnemonic, texts, ctx)]
        else:
            p = _pseudo_size(mnemonic, texts)
            names = [n for slot in _slots(p.operands) for n, _ in slot[:1]]
            ops = dict(zip(names, texts))
            expanded = p.expand(ops, ctx)
            words = []
            for k, e in enumerate(expanded):
                em, et = _split_line(e)
                words.append(encode_base(em, et, Context(labels, pc + 4 * k)))
        out.append(Line(pc, src, expanded, words))
        pc += 4 * len(words)
    return out


def listing(lines):
    """대조용 목록: 주소, 리틀 엔디언 바이트, 워드, 소스."""
    rows = []
    for ln in lines:
        for k, w in enumerate(ln.words):
            b = w.to_bytes(4, 'little')
            src = ln.source if k == 0 else '  -> ' + ln.expanded[k]
            rows.append('%08x  %s  %08x  %s' % (ln.addr + 4 * k, ' '.join('%02x' % x for x in b), w, src))
    return '\n'.join(rows)
