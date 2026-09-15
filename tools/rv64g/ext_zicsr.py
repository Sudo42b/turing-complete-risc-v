# -*- coding: utf-8 -*-
"""Zicsr: CSR 접근 명령 6종."""
from .formats import Instr, OP

E = 'Zicsr'
INSTRUCTIONS = [
    Instr('csrrw',  'CSR',  OP['SYSTEM'], 0b001, ext=E, desc='rd = csr; csr = rs1'),
    Instr('csrrs',  'CSR',  OP['SYSTEM'], 0b010, ext=E, desc='rd = csr; csr |= rs1'),
    Instr('csrrc',  'CSR',  OP['SYSTEM'], 0b011, ext=E, desc='rd = csr; csr &= ~rs1'),
    Instr('csrrwi', 'CSRI', OP['SYSTEM'], 0b101, ext=E, desc='rd = csr; csr = zimm'),
    Instr('csrrsi', 'CSRI', OP['SYSTEM'], 0b110, ext=E, desc='rd = csr; csr |= zimm'),
    Instr('csrrci', 'CSRI', OP['SYSTEM'], 0b111, ext=E, desc='rd = csr; csr &= ~zimm'),
    # 특권 명세 (M 모드 최소): 트랩 복귀와 대기
    Instr('mret', 'FIX', OP['SYSTEM'], funct7=0x30200073, ext='priv', desc='return from trap: pc = mepc, MIE = MPIE'),
    Instr('wfi',  'FIX', OP['SYSTEM'], funct7=0x10500073, ext='priv', desc='wait for interrupt (nop on this core)'),
]
