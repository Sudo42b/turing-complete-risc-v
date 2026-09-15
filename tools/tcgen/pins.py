# -*- coding: utf-8 -*-
"""부품 종류별 핀 위치 (회전 0 기준, 부품 위치에서의 상대 좌표. y 는 아래가 +).

출처: 허브 아키텍처 "RISC-V"(id 130) 의 RV32I_ALU 부품, 캠페인 Overture 레벨 정답 회로,
게임 실행 파일의 Verilog 원형(module TC_*) 에서 역추적. 확인 정도를 sure 에 적는다.
  sure=True  : 실제 배선에서 넷을 추적해 확인
  sure=False : 통계·유추 (게임에서 검증 필요)
핀 이름은 Verilog 원형의 이름을 따른다.

rows: 부품이 차지하는 행 범위(핀 포함, 배치 시 겹치지 않게). cols: 열 범위.
body: 선이 지나가면 안 되는 실제 몸통 상자 (c0, c1, r0, r1). 기본값은 왼쪽 입력 핀과 오른쪽 출력 핀 사이.
"""

PINS = {}


def _reg(kind, inputs, outputs, rows, cols, sure=True, note='', body=None):
    if body is None:
        left = [x for (x, y) in dict(inputs).values() if x < 0]
        right = [x for (x, y) in dict(outputs).values() if x > 0]
        c0 = max(left) + 1 if left else cols[0]
        c1 = min(right) - 1 if right else cols[1]
        body = (c0, c1, rows[0], rows[1])
    PINS[kind] = {'in': dict(inputs), 'out': dict(outputs), 'rows': rows, 'cols': cols, 'body': body,
                  'sure': sure, 'note': note}


# 2입력 게이트 (bit / word 동일): in0 (-1,-1) in1 (-1,1) out (2,0)
for k in ('and_bit', 'or_bit', 'xor_bit', 'nand_bit', 'nor_bit', 'xnor_bit',
          'and_word', 'or_word', 'xor_word', 'nand_word', 'nor_word', 'xnor_word',
          'equal', 'less_u', 'less_s', 'mul', 'div', 'mod'):
    _reg(k, [('in0', (-1, -1)), ('in1', (-1, 1))], [('out', (2, 0))], (-1, 1), (-1, 2))

# 3입력 게이트
for k in ('and_3_bit', 'or_3_bit'):
    _reg(k, [('in0', (-1, -1)), ('in1', (-1, 0)), ('in2', (-1, 1))], [('out', (2, 0))], (-1, 1), (-1, 2))

# 1입력
for k in ('not_bit', 'not_word', 'neg', 'inc', 'clz', 'ctz'):
    _reg(k, [('in', (-1, 0))], [('out', (2, 0))], (-1, 1), (-1, 2))

# 시프트: in (-1,-1) amount (-1,1) out (2,0)
for k in ('lsl', 'lsr', 'asr', 'rol', 'ror'):
    _reg(k, [('in', (-1, -1)), ('amount', (-1, 1))], [('out', (2, 0))], (-1, 1), (-1, 2))

# 덧셈기: cin (0,-2) in0 (-1,-1) in1 (-1,1) out (2,0). cout 은 미확인 (0,2)로 추정
_reg('add', [('cin', (0, -2)), ('in0', (-1, -1)), ('in1', (-1, 1))], [('out', (2, 0)), ('cout', (0, 2))], (-2, 2), (-1, 2),
     note='cout 위치는 추정')

# mux: select (-1,-1) in0 (-1,0) in1 (-1,1) out (2,0). select=1 이면 in1
_reg('mux', [('select', (-1, -1)), ('in0', (-1, 0)), ('in1', (-1, 1))], [('out', (2, 0))], (-1, 1), (-1, 2))

# 스위치: in (-1,0) enable (0,1) out (2,0)
for k in ('switch_bit', 'switch_word'):
    _reg(k, [('in', (-1, 0)), ('enable', (0, 1))], [('out', (2, 0))], (-1, 1), (-1, 2))

# 레지스터: save (-3,-1) save_value (-3,0) out (3,0)
_reg('register_word', [('save', (-3, -1)), ('save_value', (-3, 0))], [('out', (3, 0))], (-2, 2), (-3, 3))
_reg('register_bit', [('save', (-3, -1)), ('in', (-3, 0))], [('out', (3, 0))], (-2, 2), (-3, 3), sure=False)
_reg('counter', [('overwrite', (-3, -1)), ('overwrite_value', (-3, 0))], [('out', (3, 0))], (-2, 2), (-3, 3))

# 상수·On/Off
_reg('on', [], [('out', (1, 0))], (-1, 1), (-2, 1))
_reg('off', [], [('out', (1, 0))], (-1, 1), (-2, 1))
_reg('constant', [], [('out', (3, 0))], (-2, 2), (-4, 3), sure=False, note='출력 핀 위치 추정')

# 정적 인덱서: in (-2,0) out (2,0). settings[0] = 시프트(양수 = 오른쪽), word_size = 출력 폭
_reg('static_indexer', [('in', (-2, 0))], [('out', (2, 0))], (-1, 1), (-3, 3), sure=False, note='입력 핀 -2 또는 -3')

# 디코더 3: dis (0,-4) sel (-1,-2) out0..7 = (1,-3)..(1,4)
_reg('decoder_3', [('dis', (0, -4)), ('sel', (-1, -2))], [('out%d' % k, (1, k - 3)) for k in range(8)], (-5, 5), (-2, 2))
_reg('decoder_2', [('sel', (-1, -1))], [('out%d' % k, (1, k - 1)) for k in range(4)], (-3, 3), (-2, 2), sure=False)
_reg('decoder_1', [('select', (-1, 0))], [('out0', (1, 0)), ('out1', (1, 1))], (-2, 2), (-2, 2), sure=False)

# 비트 분리/결합 8: in (-1,0), out0..7 = (1,-3)..(1,4) / in0..7 = (-1,-3)..(-1,4), out (1,0)
_reg('splitter_bit_8', [('in', (-1, 0))], [('out%d' % k, (1, k - 3)) for k in range(8)], (-5, 5), (-1, 1))
_reg('maker_bit_8', [('in%d' % k, (-1, k - 3)) for k in range(8)], [('out', (1, 0))], (-5, 5), (-1, 1), sure=False)
_reg('splitter_bit_4', [('in', (-1, 0))], [('out%d' % k, (1, k - 1)) for k in range(4)], (-3, 3), (-1, 1), sure=False)
_reg('maker_bit_4', [('in%d' % k, (-1, k - 1)) for k in range(4)], [('out', (1, 0))], (-3, 3), (-1, 1), sure=False)
_reg('splitter_bit_2', [('in', (-1, 0))], [('out0', (1, -1)), ('out1', (1, 0))], (-2, 2), (-1, 1), sure=False)
_reg('maker_bit_2', [('in0', (-1, -1)), ('in1', (-1, 0))], [('out', (1, 0))], (-2, 2), (-1, 1), sure=False)

# 워드 분리/결합
_reg('splitter_word_2', [('in', (-1, 0))], [('out0', (1, -1)), ('out1', (1, 0))], (-2, 2), (-1, 1))
_reg('maker_word_2', [('in0', (-1, -1)), ('in1', (-1, 0))], [('out', (1, 0))], (-2, 2), (-1, 1))
_reg('splitter_word_4', [('in', (-1, 0))], [('out%d' % k, (1, k - 1)) for k in range(4)], (-3, 3), (-1, 1), sure=False)
_reg('maker_word_4', [('in%d' % k, (-1, k - 1)) for k in range(4)], [('out', (1, 0))], (-3, 3), (-1, 1), sure=False)
_reg('splitter_word_8', [('in', (-1, 0))], [('out%d' % k, (1, k - 3)) for k in range(8)], (-5, 5), (-1, 1), sure=False)
_reg('maker_word_8', [('in%d' % k, (-1, k - 3)) for k in range(8)], [('out', (1, 0))], (-5, 5), (-1, 1), sure=False)
_reg('concatenator_2', [('in0', (-1, -1)), ('in1', (-1, 0))], [('out', (1, 0))], (-2, 2), (-1, 1), sure=False)

# 커스텀 부품 안의 입출력 핀
_reg('cc_input', [], [('out', (3, 0))], (-4, 4), (-4, 4))
_reg('cc_output', [('in', (-3, 0))], [], (-4, 4), (-4, 4))

# 아키텍처 레벨 입출력 (Level input / output, 'switched' 변형): 값 핀만 확인
_reg('level_input_switched', [], [('out', (3, 0))], (-3, 3), (-4, 4), sure=False, note='enable 핀 미확인')
_reg('level_output_switched', [('in', (-3, 0))], [], (-3, 3), (-4, 4), sure=False, note='enable 핀 미확인')

# RAM 과 포트. 포트는 RAM 과 같은 x 에 RAM 위쪽으로 쌓는다.
# load_port: enable (-15,-1) address (-15,0) out (16,-1)   store_port: enable (-15,-1) address (-15,0) data (-15,1)
_reg('ram', [], [], (-9, 9), (-15, 15), note='핀 없음. 크기 31x19 (sprite)')
_reg('load_port', [('enable', (-15, -1)), ('address', (-15, 0))], [('out', (16, -1))], (-1, 0), (-17, 17))
_reg('store_port', [('enable', (-15, -1)), ('address', (-15, 0)), ('data', (-15, 1))], [], (-1, 1), (-17, 17))

_reg('halt', [('in', (-1, 0))], [], (-1, 1), (-2, 1), sure=False)


def pin(kind, name):
    p = PINS[kind]
    if name in p['in']:
        return p['in'][name], 'in'
    if name in p['out']:
        return p['out'][name], 'out'
    raise KeyError('%s has no pin %r (in=%s out=%s)' % (kind, name, list(p['in']), list(p['out'])))
