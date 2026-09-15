# -*- coding: utf-8 -*-
"""순수 파이썬 snappy 원시 블록 코덱 (게임의 supersnappy 와 호환).

압축은 리터럴만 쓰는 최소 구현이다. 형식상 합법이고 게임이 그대로 읽는다.
크기가 중요하면 나중에 매치 탐색을 넣는다.
"""


def _read_varint(data, i):
    result = 0
    shift = 0
    while True:
        b = data[i]
        i += 1
        result |= (b & 0x7F) << shift
        if b < 0x80:
            return result, i
        shift += 7


def _write_varint(n):
    out = bytearray()
    while n >= 0x80:
        out.append((n & 0x7F) | 0x80)
        n >>= 7
    out.append(n)
    return bytes(out)


def decompress(data):
    """snappy 원시 블록 -> bytes."""
    total, i = _read_varint(data, 0)
    out = bytearray()
    n = len(data)
    while i < n:
        tag = data[i]
        i += 1
        kind = tag & 3
        if kind == 0:                         # literal
            length = tag >> 2
            if length < 60:
                length += 1
            else:
                nbytes = length - 59
                length = int.from_bytes(data[i:i + nbytes], 'little') + 1
                i += nbytes
            out += data[i:i + length]
            i += length
            continue
        if kind == 1:                         # copy, 1-byte offset
            length = ((tag >> 2) & 7) + 4
            offset = ((tag >> 5) << 8) | data[i]
            i += 1
        elif kind == 2:                       # copy, 2-byte offset
            length = (tag >> 2) + 1
            offset = int.from_bytes(data[i:i + 2], 'little')
            i += 2
        else:                                 # copy, 4-byte offset
            length = (tag >> 2) + 1
            offset = int.from_bytes(data[i:i + 4], 'little')
            i += 4
        if offset == 0 or offset > len(out):
            raise ValueError('bad snappy copy offset %d at %d' % (offset, i))
        for _ in range(length):               # 겹치는 복사도 바이트 단위로 처리
            out.append(out[-offset])
    if len(out) != total:
        raise ValueError('snappy length mismatch: header %d, got %d' % (total, len(out)))
    return bytes(out)


def compress(data):
    """bytes -> snappy 원시 블록 (리터럴만)."""
    out = bytearray(_write_varint(len(data)))
    i = 0
    n = len(data)
    while i < n:
        chunk = data[i:i + 65536]
        length = len(chunk)
        if length <= 60:
            out.append((length - 1) << 2)
        elif length <= 256:
            out.append(60 << 2)
            out += (length - 1).to_bytes(1, 'little')
        else:
            out.append(61 << 2)
            out += (length - 1).to_bytes(2, 'little')
        out += chunk
        i += length
    return bytes(out)


if __name__ == '__main__':
    import os
    sample = os.urandom(1000) + b'\x00' * 5000 + bytes(range(256)) * 300
    assert decompress(compress(sample)) == sample
    assert decompress(compress(b'')) == b''
    print('snappy codec ok')
