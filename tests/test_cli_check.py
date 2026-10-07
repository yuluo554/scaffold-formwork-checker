# -*- coding: utf-8 -*-
"""M3 CLI 守门：sfc check / sfc grade 退出码与输出结构（口径沿用 0/1/2）。"""

import json
import os

from scaffold_formwork_checker.cli import (
    EXIT_DEGRADED,
    EXIT_INPUT_ERROR,
    EXIT_OK,
    main,
)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SYNTH_DIR = os.path.join(REPO_ROOT, "data", "synthetic")


def _fx(name):
    return os.path.join(SYNTH_DIR, name + ".docx")


def _report(capsys, argv):
    code = main(argv)
    out = capsys.readouterr().out
    return code, json.loads(out)


# ---- sfc check ----

def test_check_clean_fixture_exits_ok(capsys):
    code, report = _report(capsys, ["check", _fx("SY-clean-01")])
    assert code == EXIT_OK
    assert report["summary"]["violation"] == 0
    assert report["summary"]["confirmations"] == 0
    assert report["summary"]["all_pass"] is True
    assert report["scheme_card"]["card_type"] == "scheme"
    assert report["calcbook_card"]["card_type"] == "calcbook"
    assert report["grading"]["level"] == "none"
    assert report["file"].endswith("SY-clean-01.docx")


def test_check_defect_fixture_exits_degraded(capsys):
    code, report = _report(capsys, ["check", _fx("SY-two-sheets-01")])
    assert code == EXIT_DEGRADED
    assert report["summary"]["violation"] == 1
    ids = {f["rule_id"] for f in report["findings"] if f["verdict"] != "pass"}
    assert "R-consistency-step" in ids


def test_check_grading_fixture_reports_violation_and_trigger(capsys):
    code, report = _report(capsys, ["check", _fx("SY-grading-missing-01")])
    assert code == EXIT_DEGRADED
    non_pass = {f["rule_id"]: f["verdict"] for f in report["findings"]
                if f["verdict"] != "pass"}
    assert non_pass == {"R-grading-expert-review": "violation",
                        "G-pan-luodi-50": "triggered"}
    assert report["grading"]["level"] == "chaoguimo"


def test_check_missing_file_exits_input_error(capsys):
    assert main(["check", os.path.join(SYNTH_DIR, "no-such.docx")]) == EXIT_INPUT_ERROR


def test_check_garbage_file_exits_input_error(tmp_path, capsys):
    bad = tmp_path / "bad.docx"
    bad.write_bytes(b"not a docx")
    assert main(["check", str(bad)]) == EXIT_INPUT_ERROR
    assert "解析失败" in capsys.readouterr().err


def test_check_unsupported_extension_exits_input_error(tmp_path, capsys):
    bad = tmp_path / "scheme.rtf"
    bad.write_text("x", encoding="utf-8")
    assert main(["check", str(bad)]) == EXIT_INPUT_ERROR


def test_check_bad_data_dir_exits_input_error(capsys):
    assert main(["check", _fx("SY-clean-01"),
                 "--data-dir", "no-such-dir"]) == EXIT_INPUT_ERROR


def test_check_indent_zero_single_line(capsys):
    code = main(["check", _fx("SY-clean-01"), "--indent", "0"])
    out = capsys.readouterr().out.strip()
    assert code == EXIT_OK
    assert out.count("\n") == 0


# ---- sfc grade ----

def test_grade_definite_exits_ok(capsys):
    code, result = _report(capsys, ["grade", _fx("SY-clean-01")])
    assert code == EXIT_OK
    assert result["status"] == "definite"
    assert result["level"] == "none"
    assert result["verdict"] == "pass"


def test_grade_chaoguimo_exits_ok_with_duty(capsys):
    code, result = _report(capsys, ["grade", _fx("SY-grading-missing-01")])
    assert code == EXIT_OK  # 判定本身完成（违规与否属 sfc check 职责）
    assert result["level"] == "chaoguimo"
    assert result["rule_id"] == "G-pan-luodi-50"
    assert result["actual"] == 56.0


def test_grade_param_override(capsys):
    """--param 覆盖判定参数：干净文档被覆盖成超规模 → chaoguimo。"""
    code, result = _report(
        capsys, ["grade", _fx("SY-clean-01"), "--param", "build_height=56"])
    assert code == EXIT_OK
    assert result["level"] == "chaoguimo"


def test_grade_pending_exits_degraded(capsys):
    """文档不含搭设高度 → 分级待人工确认 → exit 1。"""
    code, result = _report(
        capsys, ["grade", _fx("SY-clean-01"),
                 "--param", "build_height=not-a-number"])
    assert code == EXIT_DEGRADED
    assert result["status"] == "pending"


def test_grade_missing_file_exits_input_error(capsys):
    assert main(["grade", "no-such.docx"]) == EXIT_INPUT_ERROR


def test_grade_bad_param_form_exits_input_error(capsys):
    assert main(["grade", _fx("SY-clean-01"), "--param", "novalue"]) == EXIT_INPUT_ERROR
