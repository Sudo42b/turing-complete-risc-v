# -*- coding: utf-8 -*-
"""넷리스트 -> 배치 -> 배선 -> Save.

배선 규칙 (게임 관찰 결과에 근거):
  - 선은 끝점에서만 연결된다. 교차는 연결이 아니다. 끝점이 다른 선의 몸통에 닿으면 연결(T 접합).
  - 그래서 "다른 넷의 끝점 위를 지나가지 않기"만 지키면 된다.

배치: 부품을 한 열(x=0)에 세로로 쌓는다. 부품마다 자기 행 띠를 독점한다. 입력 핀은 왼쪽,
출력 핀은 오른쪽에 있으므로, 한 행에는 입력 핀 최대 1개, 출력 핀 최대 1개만 있다.
배선: 넷마다 오른쪽 레인 x, 위쪽 고속도로 y, 왼쪽 레인 x 를 하나씩 독점한다.
  출력 핀 → 오른쪽으로 → 오른쪽 레인 → 위로 → 고속도로 → 왼쪽으로 → 왼쪽 레인 → 아래로 →
  가장 아래 싱크 행 → 오른쪽으로 → 싱크 핀 (한 선). 나머지 싱크는 왼쪽 레인에서 갈라진다.
  드라이버가 여럿인 넷(스위치 버스)은 가장 아래 드라이버가 몸통을 만들고 나머지는 오른쪽 레인에 닿는다.
"""
import random
from dataclasses import dataclass, field

from .pins import PINS, pin
from tcsave.save16 import Component, Point, Save, Wire, serialize

DIR_R, DIR_D, DIR_L, DIR_U = 0, 2, 4, 6


@dataclass
class Comp:
    name: str
    kind: str
    word_size: int = 1
    settings: list = field(default_factory=list)
    label: str = ''
    ui_order: int = 0
    buffer_size: int = 0
    init_data: str = 'zeroes'
    little_endian: bool = False
    x: int = 0
    y: int = 0

    def pin_at(self, pname):
        (dx, dy), _ = pin(self.kind, pname)
        return Point(self.x + dx, self.y + dy)


@dataclass
class Net:
    name: str
    drivers: list = field(default_factory=list)   # [(comp, pin)]
    sinks: list = field(default_factory=list)     # [(comp, pin)]


class Design:
    def __init__(self, name, custom_id=None, description=''):
        self.name = name
        self.custom_id = custom_id if custom_id is not None else random.getrandbits(62) | 1
        self.description = description
        self.comps = []
        self.by_name = {}
        self.nets = []
        self.net_by_name = {}

    # ----- 넷리스트 -----
    def add(self, name, kind, ws=1, settings=None, label='', **kw):
        if kind not in PINS:
            raise KeyError('unknown kind %s' % kind)
        c = Comp(name, kind, ws, list(settings or []), label or '', **kw)
        if name in self.by_name:
            raise KeyError('duplicate component %s' % name)
        self.comps.append(c)
        self.by_name[name] = c
        return c

    def net(self, name):
        if name not in self.net_by_name:
            n = Net(name)
            self.nets.append(n)
            self.net_by_name[name] = n
        return self.net_by_name[name]

    def connect(self, net_name, *endpoints):
        """endpoints: 'comp.pin' 문자열. 출력 핀은 드라이버, 입력 핀은 싱크."""
        n = self.net(net_name)
        for ep in endpoints:
            cname, pname = ep.split('.')
            c = self.by_name[cname]
            _, direction = pin(c.kind, pname)
            (n.drivers if direction == 'out' else n.sinks).append((c, pname))
        return n

    # ----- 배치 -----
    def place(self, gap=1, order=None):
        """한 열에 세로로 쌓는다. order 로 순서를 줄 수 있다."""
        comps = [self.by_name[n] for n in order] if order else self.comps
        y = 0
        for c in comps:
            r0, r1 = PINS[c.kind]['rows']
            c.x = 0
            c.y = y - r0
            y = c.y + r1 + 1 + gap
        self.height = y

    # ----- 배선 -----
    def route(self):
        wires = []
        n_nets = len(self.nets)
        max_right = max(c.x + PINS[c.kind]['cols'][1] for c in self.comps)
        min_left = min(c.x + PINS[c.kind]['cols'][0] for c in self.comps)
        min_row = min(c.y + PINS[c.kind]['rows'][0] for c in self.comps)
        right_lane0 = max_right + 3
        left_lane0 = min_left - 3
        highway0 = min_row - 3
        self.bounds = None
        for i, n in enumerate(self.nets):
            if not n.drivers:
                raise ValueError('net %s has no driver' % n.name)
            if not n.sinks:
                continue
            rlane = right_lane0 + i
            llane = left_lane0 - i
            hwy = highway0 - i
            drivers = sorted(n.drivers, key=lambda cp: cp[0].pin_at(cp[1]).y)
            sinks = sorted(n.sinks, key=lambda cp: cp[0].pin_at(cp[1]).y)
            src = drivers[-1][0].pin_at(drivers[-1][1])          # 가장 아래 드라이버
            last = sinks[-1][0].pin_at(sinks[-1][1])              # 가장 아래 싱크
            # 몸통: src → 오른쪽 레인 → 고속도로 → 왼쪽 레인 → 마지막 싱크
            segs = []
            segs.append((DIR_R, rlane - src.x))
            segs.append((DIR_U, src.y - hwy))
            segs.append((DIR_L, rlane - llane))
            segs.append((DIR_D, last.y - hwy))
            segs.append((DIR_R, last.x - llane))
            wires.append(Wire(src, [s for s in segs if s[1] > 0], color=0, comment=''))
            # 다른 드라이버: 오른쪽 레인에 닿는 짧은 선
            for c, p in drivers[:-1]:
                q = c.pin_at(p)
                wires.append(Wire(q, [(DIR_R, rlane - q.x)]))
            # 다른 싱크: 왼쪽 레인에서 가지
            for c, p in sinks[:-1]:
                q = c.pin_at(p)
                wires.append(Wire(Point(llane, q.y), [(DIR_R, q.x - llane)]))
        self.wires = wires
        xs = [p.x for w in wires for p in (w.start, w.finish)] + [c.x for c in self.comps]
        ys = [p.y for w in wires for p in (w.start, w.finish)] + [c.y for c in self.comps]
        self.bounds = (min(xs), min(ys), max(xs), max(ys))
        return wires

    # ----- 검증 -----
    def validate(self):
        """모든 선 끝점이 자기 넷의 핀이거나 자기 넷의 선 위에 있고, 다른 넷의 끝점을 지나지 않는지."""
        pin_owner = {}
        for n in self.nets:
            for c, p in n.drivers + n.sinks:
                q = c.pin_at(p)
                if q in pin_owner and pin_owner[q] is not n:
                    raise ValueError('pin %s used by two nets' % (q,))
                pin_owner[q] = n
        # 각 넷의 점 집합
        net_points = {}
        net_ends = {}
        wire_net = {}
        for n in self.nets:
            net_points[n.name] = set()
            net_ends[n.name] = set()
        # 선 -> 넷 : 끝점이 핀이면 그 핀의 넷
        for w in self.wires:
            owner = None
            for e in (w.start, w.finish):
                if e in pin_owner:
                    owner = pin_owner[e]
            wire_net[id(w)] = owner
        # 핀에 닿지 않는 선(가지)은 몸통에 닿는 넷을 찾는다 (반복)
        changed = True
        while changed:
            changed = False
            for w in self.wires:
                if wire_net[id(w)] is not None:
                    continue
                for w2 in self.wires:
                    n2 = wire_net[id(w2)]
                    if n2 is None or w2 is w:
                        continue
                    pts = set(w2.points())
                    if w.start in pts or w.finish in pts:
                        wire_net[id(w)] = n2
                        changed = True
                        break
        for w in self.wires:
            n = wire_net[id(w)]
            if n is None:
                raise ValueError('wire %s->%s belongs to no net' % (w.start, w.finish))
            net_points[n.name].update(w.points())
            net_ends[n.name].update((w.start, w.finish))
        # 다른 넷의 끝점이 내 점 위에 있으면 오류
        for a in self.nets:
            for b in self.nets:
                if a is b:
                    continue
                bad = net_ends[a.name] & net_points[b.name]
                if bad:
                    raise ValueError('net %s endpoint %s lies on net %s' % (a.name, sorted(bad)[0], b.name))
        # 다른 넷의 핀 위를 지나지 않기
        for n in self.nets:
            for q, owner in pin_owner.items():
                if owner is not n and q in net_points[n.name]:
                    raise ValueError('net %s passes over pin %s of net %s' % (n.name, q, owner.name))
        # 부품 몸통 위를 지나지 않기 (핀 제외)
        bodies = {}
        for c in self.comps:
            c0, c1, r0, r1 = PINS[c.kind]['body']
            for yy in range(c.y + r0, c.y + r1 + 1):
                for xx in range(c.x + c0, c.x + c1 + 1):
                    bodies[Point(xx, yy)] = c
        for n in self.nets:
            for q in net_points[n.name]:
                if q in bodies and q not in pin_owner:
                    raise ValueError('net %s passes over body of %s at %s' % (n.name, bodies[q].name, q))
        return True

    # ----- 출력 -----
    def to_save(self, foundry=True):
        s = Save()
        s.custom_id = self.custom_id if foundry else 0
        s.description = self.description
        s.gate = 99999
        s.delay = 99999
        s.menu_visible = True
        s.clock_speed = 10_000_000
        if foundry:
            for x in range(15, 19):           # 허브 부품의 기본 도형 (4x6 블록)
                for y in range(13, 19):
                    s.design[x][y] = 0x90
        ids = set()
        for c in self.comps:
            pid = random.getrandbits(62) | 1
            while pid in ids:
                pid = random.getrandbits(62) | 1
            ids.add(pid)
            comp = Component(kind=c.kind, position=Point(c.x, c.y), rotation=0, permanent_id=pid,
                             user_label=c.label, settings=list(c.settings), word_size=c.word_size,
                             ui_order=c.ui_order, buffer_size=c.buffer_size, init_data=c.init_data,
                             is_little_endian=c.little_endian, gate_variant=-1, delay_variant=0)
            s.components.append(comp)
        s.wires = list(self.wires)
        return s

    def build(self, foundry=True, order=None):
        self.place(order=order)
        self.route()
        self.validate()
        return self.to_save(foundry)

    def write(self, path, foundry=True, order=None):
        data = serialize(self.build(foundry, order))
        with open(path, 'wb') as fh:
            fh.write(data)
        return data
