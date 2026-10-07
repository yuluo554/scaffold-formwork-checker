# -*- coding: utf-8 -*-
"""M4 CLI 守门：sfc bench 退出码与输出结构（0=全达标 / 2=数据目录不可用）。

DoD ①"断网跑通"守门：子进程带不可路由代理环境变量跑 bench——核心管线
零网络依赖，若任何环节发起 API/网络请求即失败。
"""

import json
import os
import subprocess
import sys

from scaffold_formwork_checker.cli import EXIT_DEGRADED, EXIT_INPUT_ERROR, EXIT_OK, main

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_bench_exits_ok_with_full_metrics(capsys):
    assert main(["bench", "--data-dir", os.path.join(REPO_ROOT, "data")]) == EXIT_OK
    out = json.loads(capsys.readouterr().out)
    assert set(out["suites"]) == {"examples", "synthetic", "grading"}
    assert out["all_pass"] is True
    assert all(out["targets"].values())


def test_bench_indent_zero_single_line(capsys):
    code = main(["bench", "--indent", "0"])
    out = capsys.readouterr().out.strip()
    assert code == EXIT_OK
    assert out.count("\n") == 0


def test_bench_missing_data_dir_exits_input_error(capsys):
    assert main(["bench", "--data-dir", "no-such-dir"]) == EXIT_INPUT_ERROR
    assert "数据目录不可用" in capsys.readouterr().err


def test_bench_offline_with_broken_proxies():
    """断网模拟：不可路由代理 + 全部 NO_PROXY 剥离，bench 仍全绿（零 API）。"""
    env = dict(os.environ)
    env.update({
        "PYTHONDONTWRITEBYTECODE": "1",
        "HTTP_PROXY": "http://127.0.0.1:9",
        "HTTPS_PROXY": "http://127.0.0.1:9",
        "http_proxy": "http://127.0.0.1:9",
        "https_proxy": "http://127.0.0.1:9",
        "ALL_PROXY": "http://127.0.0.1:9",
    })
    env.pop("NO_PROXY", None)
    env.pop("no_proxy", None)
    proc = subprocess.run(
        [sys.executable, "-m", "scaffold_formwork_checker", "bench",
         "--data-dir", os.path.join(REPO_ROOT, "data"), "--indent", "0"],
        capture_output=True, text=True, timeout=300, env=env, cwd=REPO_ROOT,
    )
    assert proc.returncode == EXIT_OK, proc.stderr
    outcome = json.loads(proc.stdout)
    assert outcome["all_pass"] is True


def test_bench_degraded_exit_when_target_fails(capsys, monkeypatch):
    """指标未达标 → exit 1（完整指标仍输出）。注入假失败：门限抬到不可达。"""
    from scaffold_formwork_checker import bench
    monkeypatch.setattr(bench, "BENCH_TARGETS",
                        dict(bench.BENCH_TARGETS, grading_pass_rate=2.0))
    code = main(["bench", "--data-dir", os.path.join(REPO_ROOT, "data")])
    captured = capsys.readouterr()  # 只消费一次（二次调用 err 为空）
    out = json.loads(captured.out)
    assert code == EXIT_DEGRADED
    assert out["all_pass"] is False
    assert out["targets"]["grading_pass_rate"] is False
    assert "grading_pass_rate" in captured.err
