# -*- coding: utf-8 -*-
"""Zifencei: fence.i (이 코어는 하버드 구조라 nop 로 구현)."""
from .formats import Instr, OP

INSTRUCTIONS = [
    Instr('fence.i', 'FIX', OP['MISC_MEM'], funct7=0x0000100F, ext='Zifencei',
          desc='instruction-fetch fence (nop: program memory is separate)'),
]
