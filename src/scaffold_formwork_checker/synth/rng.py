# -*- coding: utf-8 -*-
"""确定性 RNG：SplitMix64（禁 stdlib random——其序列不承诺跨版本一致）。

用法：
    rng = SplitMix64(seed)
    rng.next_uint64()      # 原始 64 位
    rng.below(n)           # [0, n) 均匀下标（模板池选择）

纪律：同一种子序列跨 Python 版本/平台逐位一致（纯整数运算）。
"""

_MASK64 = (1 << 64) - 1
_GOLDEN = 0x9E3779B97F4A7C15


class SplitMix64(object):
    def __init__(self, seed):
        self._state = int(seed) & _MASK64

    def next_uint64(self):
        self._state = (self._state + _GOLDEN) & _MASK64
        z = self._state
        z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & _MASK64
        z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & _MASK64
        return z ^ (z >> 31)

    def below(self, n):
        """[0, n) 下标。n 为正 int；池子小，取模偏差忽略（v1 注释保留）。"""
        if n <= 0:
            raise ValueError("n must be positive")
        return self.next_uint64() % n

    def pick(self, pool):
        """从 tuple/list 池中确定性取一元素。禁 set（迭代序不确定）。"""
        if not isinstance(pool, (tuple, list)):
            raise TypeError("pool 必须是 tuple/list（禁 set 迭代序）")
        return pool[self.below(len(pool))]
