# -*- coding: utf-8 -*-
"""D 확장(배정도). F 표를 fmt = 01 로 재사용한다."""
from .ext_f import fp_instructions

INSTRUCTIONS = fp_instructions('D', '.d', 0b01, '64')
