# -*- coding: utf-8 -*-
"""어셈블리 파일을 참조 인코더로 기계어로 바꿔 대조표를 출력한다.

    python tools/rv_encode.py tests/encode_check.asm            # 표준 출력
    python tools/rv_encode.py tests/encode_check.asm -o out.txt # 파일로
    python tools/rv_encode.py tests/encode_check.asm --origin 0x1000

출력 형식:  주소  리틀엔디언 바이트 4개  32비트 워드  소스
게임의 기계어 뷰(또는 프로그램 RAM 내용)와 바이트 열을 비교하면 된다.
"""
import argparse
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rv64g.encoder import assemble, listing, AsmError      # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('asm')
    ap.add_argument('-o', '--output')
    ap.add_argument('--origin', default='0')
    args = ap.parse_args()
    src = io.open(args.asm, encoding='utf-8').read()
    try:
        lines = assemble(src, origin=int(args.origin, 0))
    except AsmError as e:
        print('error:', e)
        return 1
    text = listing(lines)
    if args.output:
        with io.open(args.output, 'w', encoding='utf-8', newline='\n') as fh:
            fh.write(text + '\n')
        print('wrote', args.output, '(%d words)' % sum(len(l.words) for l in lines))
    else:
        print(text)
    return 0


if __name__ == '__main__':
    sys.exit(main())
