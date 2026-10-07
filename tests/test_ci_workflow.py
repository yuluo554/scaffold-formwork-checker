# -*- coding: utf-8 -*-
"""CI workflow 守门测试（M6 发布门，发票台账实录①的前置保险）。

workflow YAML 非法（如 step 名含未引号冒号+空格）时 GitHub 不建任何 job、run 0 秒失败，
且文件字节与 workflow state 都看不出问题——只有真解析能暴露。断言：
- 全部 workflow 可被 PyYAML 解析；
- 每个 job 有 runs-on 与 steps（防"解析过但空壳"）；
- checkout 带 fetch-depth: 0（脱敏历史扫描测试依赖全量历史）；
- 安装步骤覆盖测试期 extras（.[dev]，防"悄悄少跑"）。
"""
import glob
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
WORKFLOWS = sorted(glob.glob(str(REPO / ".github" / "workflows" / "*.yml")))


def test_workflows_exist():
    assert WORKFLOWS, "未找到 .github/workflows/*.yml"


def test_workflows_parse_and_jobs_wellformed():
    for f in WORKFLOWS:
        doc = yaml.safe_load(Path(f).read_text(encoding="utf-8"))
        assert isinstance(doc, dict) and doc.get("jobs"), "无 jobs: %s" % f
        for name, job in doc["jobs"].items():
            assert job.get("runs-on"), "%s job %s 缺 runs-on" % (f, name)
            assert job.get("steps"), "%s job %s 缺 steps" % (f, name)


def test_checkout_fetches_full_history():
    for f in WORKFLOWS:
        doc = yaml.safe_load(Path(f).read_text(encoding="utf-8"))
        for job in doc["jobs"].values():
            for step in job.get("steps", []):
                if isinstance(step, dict) and "checkout@" in str(step.get("uses", "")):
                    assert step.get("with", {}).get("fetch-depth") == 0, (
                        "%s checkout 未取全量历史（历史扫描测试会被浅克隆静默削弱）" % f)


def test_ci_installs_dev_extras():
    for f in WORKFLOWS:
        doc = yaml.safe_load(Path(f).read_text(encoding="utf-8"))
        text = Path(f).read_text(encoding="utf-8")
        assert '.[dev]' in text, "%s 未安装 .[dev]（测试期依赖缺失会静默少跑）" % f
