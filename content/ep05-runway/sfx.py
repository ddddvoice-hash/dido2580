"""금속 기체 효과음 — 코드 합성 (14.4–19.0초 대치 구간용).

대표 지시(11/18): 육중한 금속 마찰음, 기계 구동음, 공간 잔향, 충돌음 중심. 저가형 전자음(순수 사인 삑) 금지.
그래서 모든 음은 잡음 기반 + 비정수배 공명(금속판·구조물 특성)으로 만들고, 순음은 쓰지 않는다.
"""
import numpy as np

SR = 48000
RNG = np.random.default_rng(2051)


def _bands(x, bands):
    """FFT 영역 공명 필터. bands = [(중심Hz, 폭Hz, 이득), ...]"""
    X = np.fft.rfft(x)
    fr = np.fft.rfftfreq(len(x), 1 / SR)
    H = np.zeros_like(fr)
    for c, w, g in bands:
        H += g * np.exp(-0.5 * ((fr - c) / w) ** 2)
    return np.fft.irfft(X * H, len(x)).astype(np.float32)


def _env(n, a, d):
    t = np.arange(n) / SR
    return np.minimum(1, t / max(a, 1e-4)) * np.exp(-t / d)


def _norm(x, peak=0.9):
    return (x / (np.abs(x).max() + 1e-9) * peak).astype(np.float32)


def servo(dur):
    """기계 구동음: 갈린 잡음을 기어 이빨 주기로 두드리고, 회전이 서서히 올라감(55→80Hz 대역)."""
    n = int(dur * SR); t = np.arange(n) / SR
    rate = 14 + 10 * (t / dur) ** 1.5                     # 기어 맞물림 속도 상승
    teeth = 0.55 + 0.45 * np.abs(np.sin(np.pi * np.cumsum(rate) / SR)) ** 6
    body = _bands(RNG.normal(0, 1, n), [(62, 18, 1.0), (124, 22, 0.6), (187, 30, 0.35), (410, 60, 0.18), (1350, 300, 0.05)])
    whir = _bands(RNG.normal(0, 1, n), [(780, 40, 0.25), (1530, 70, 0.12)]) * (t / dur)
    return _norm((body * teeth + whir) * np.minimum(1, t / 0.25) * np.minimum(1, (dur - t) / 0.15), 0.7)


def friction(dur):
    """육중한 금속 마찰: 스틱-슬립(불규칙하게 걸렸다 미끄러짐) 잡음 + 비정수배 금속 공명."""
    n = int(dur * SR); t = np.arange(n) / SR
    ss = np.abs(_bands(RNG.normal(0, 1, n), [(7, 4, 1.0)]))  # 느린 불규칙 압력
    ss = ss / (ss.max() + 1e-9)
    grit = _bands(RNG.normal(0, 1, n), [(338, 25, 1.0), (611, 30, 0.8), (1127, 45, 0.55), (2214, 90, 0.3), (3870, 220, 0.12)])
    low = _bands(RNG.normal(0, 1, n), [(48, 14, 1.2), (96, 20, 0.5)])
    build = np.minimum(1, t / dur) ** 1.3
    return _norm((grit * (0.25 + ss) + low) * (0.35 + 0.65 * build), 0.8)


def clang(dur=1.6, f0=1.0):
    """금속 타격: 비정수배 부분음(판·빔)을 잡음으로 들뜨게 함. 높은 부분음일수록 빨리 사라짐."""
    n = int(dur * SR)
    out = np.zeros(n, np.float32)
    for c, d, g in [(97, 1.4, 1.0), (233, 1.0, 0.7), (561, 0.6, 0.5), (1013, 0.35, 0.35), (1679, 0.2, 0.25), (2741, 0.12, 0.15)]:
        out += g * _bands(RNG.normal(0, 1, n), [(c * f0, 3 + c * 0.004, 1.0)]) * _env(n, 0.002, d)
    burst = _bands(RNG.normal(0, 1, n), [(2500, 1500, 0.6)]) * _env(n, 0.0005, 0.02)
    return _norm(out + burst, 0.9)


def impact(dur=0.6):
    """충돌: 밑바닥 쿵(잡음 기반 40Hz 대역) + 금속 타격 + 파편 잡음. 앞 67ms가 들리고 나머지는 암전 무음에 잘림."""
    n = int(dur * SR)
    boom = _bands(RNG.normal(0, 1, n), [(38, 10, 1.6), (70, 16, 0.8)]) * _env(n, 0.001, 0.35)
    debris = _bands(RNG.normal(0, 1, n), [(3000, 2000, 0.5)]) * _env(n, 0.0003, 0.05)
    return _norm(_norm(boom) + 0.8 * clang(dur, 0.8) + debris, 0.95)


def reverb(x, rt=2.2, wet=0.35, pre=0.02):
    """공간 잔향(큰 격납고 느낌): 지수 감쇠 잡음 임펄스, 좌우 따로 → 스테레오. 고역은 더 빨리 사라짐."""
    n = int(rt * SR)
    out = []
    for ch in range(2):
        ir = RNG.normal(0, 1, n) * np.exp(-np.arange(n) / SR * 6.9 / rt)
        ir = _bands(ir, [(400, 600, 1.0), (1800, 1400, 0.45)])
        ir = np.concatenate([np.zeros(int(pre * SR)), ir])
        L = len(x) + len(ir) - 1
        y = np.fft.irfft(np.fft.rfft(x, L) * np.fft.rfft(ir, L), L)
        y = y / (np.abs(y).max() + 1e-9) * np.abs(x).max()
        out.append((1 - wet) * np.pad(x, (0, len(ir) - 1)) + wet * y)
    return np.stack(out, 1).astype(np.float32)


def swell(dur):
    """각성 상승음: 역재생 잔향처럼 차오르는 잡음 + 금속 공명이 위로 미끄러짐(순음 없음)."""
    n = int(dur * SR); t = np.arange(n) / SR
    rise = (t / dur) ** 2.2
    out = np.zeros(n, np.float32)
    for c in (180, 410, 760, 1320):
        # 공명 중심이 1.6배까지 올라감 — 짧은 블록마다 필터
        blk = 4800
        for s in range(0, n, blk):
            e = min(n, s + blk)
            f = c * (1 + 0.6 * (s / n))
            out[s:e] += _bands(RNG.normal(0, 1, e - s), [(f, 6 + f * 0.01, 1.0)]) / np.sqrt(c / 180)
    air = _bands(RNG.normal(0, 1, n), [(5000, 3000, 0.3)])
    return _norm((out + air) * rise, 0.85)


def boom(dur=2.5):
    """거대화 순간: 아주 낮은 쿵 + 긴 꼬리."""
    n = int(dur * SR)
    return _norm(_bands(RNG.normal(0, 1, n), [(32, 8, 1.6), (55, 12, 0.9), (110, 25, 0.3)]) * _env(n, 0.004, 0.9), 0.95)
