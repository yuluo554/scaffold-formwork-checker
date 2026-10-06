# -*- coding: utf-8 -*-
"""synth —— 合成专项方案生成器（M1 v1，M3 消费）。

真值语义（一次定清，改语义=改口径，须同步 bench 与真值 JSON）：
- 注入缺陷记主期望（main_expect）；
- 同一注入隐含的其余结论记 also_expect（如"超规模未标注"注入同时隐含
  危大分级=超过一定规模 的判定期望）；
- 评测按"文档全部非 pass 集合"对账：引擎报出的所有非 pass 项必须恰好等于
  main_expect ∪ also_expect（防漏报伪装成正确，也防误报）。

确定性纪律（字节冻结根基）：
- 禁 stdlib random、禁 set/dict 迭代序（模板池一律 tuple/list + 确定性 RNG 下标）、
  禁系统时钟；自研 SplitMix64（见 rng.py）；
- docx 落盘后统一重写 zip 条目时间戳为 (1980,1,1,0,0,0) 并覆写
  docProps/core.xml、docProps/app.xml 为固定内容（无生成时间）；
- 同一 spec 两次构建逐字节一致（守门测试 tests/test_synth_freeze.py）；
- data/synthetic/ 为冻结 fixtures，禁止手改；改体例→用固定 seed 重新生成整目录提交。

参数合法性：模板池取值均来自条款库已核对限值（data/knowledge/clauses/thresholds.json），
来源表在 generator.py 池定义处逐项注释 threshold_id。
"""

from .rng import SplitMix64
from .generator import generate_all, build_fixture_bytes, FIXTURE_SPECS

__all__ = ["SplitMix64", "generate_all", "build_fixture_bytes", "FIXTURE_SPECS"]
