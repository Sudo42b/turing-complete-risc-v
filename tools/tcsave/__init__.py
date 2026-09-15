# -*- coding: utf-8 -*-
"""Turing Complete 세이브(circuit.data, 형식 버전 16) 읽기/쓰기.

게임 개발자가 공개한 save_monger(https://github.com/Stuffe/save_monger, CC0)의
common.nim / versions/v16.nim / state_to_binary 를 파이썬으로 옮긴 것이다.

파일 = 버전 바이트(16) + snappy 원시 블록(압축 해제하면 리틀 엔디언 고정폭 필드 나열).
"""
from .save16 import (Component, Wire, Point, Save, parse, serialize, load, dump,
                     KIND_NAMES, KIND_IDS, DIRECTIONS)

__all__ = ['Component', 'Wire', 'Point', 'Save', 'parse', 'serialize', 'load', 'dump',
           'KIND_NAMES', 'KIND_IDS', 'DIRECTIONS']
