# -*- coding: utf-8 -*-
"""合成专项施工方案生成器 v1（确定性、字节冻结）。

- 体例：python-docx 生成专项施工方案 docx（工程概况/编制依据/搭设参数表/
  构造措施/危大工程管理/验算书六章），模板池按 SplitMix64 确定性抽取；
- 注入缺陷（每例主期望 main_expect + 隐含 also_expect，真值 JSON 随 fixture 落盘）：
  1) step_over        threshold  步距超构造限值（表6.1.1-1 常用尺寸上限 1.8m）
  2) walltie_over     threshold  连墙件竖向间距超限（表6.4.2 双排落地 3h）
  3) brace_missing    presence   漏剪刀撑（6.6.2/6.6.3）
  4) two_sheets       consistency 验算书步距与方案正文不一致（两张皮）
  5) grading_missing  grading    搭设高度≥50m 应专家论证而方案未标注（37号令§12）
  6) clean            干净对照（0 缺陷，误报率分母）
- 落盘无时间戳：zip 全条目 date_time=(1980,1,1,0,0,0)，core.xml/app.xml 覆写固定内容。

模板池合法性与条款库对应（data/knowledge/clauses/thresholds.json）：
- PARAM_POOLS 步距/纵距/横距组合 ⊆ 表6.1.1-1（T-JGJ130-construction-dims）；
- 连墙件竖向=2h/3h、水平=3la ⊆ 表6.4.2（T-JGJ130-walltie-spacing）；
- 钢管 48.3×3.6、Q235A（T-JGJ130-pipe-spec）；
- 脚手板 0.30、装修荷载 2.0（T-JGJ130-dead-loads / T-JGJ130-live-loads）。
"""

import io
import json
import zipfile

from .rng import SplitMix64

# 固定 seed（台账登记；变更=重新生成整目录提交）
FIXTURE_SEED = 20261006

# zip 固定元数据（无时间戳纪律）
_ZIP_DATE = (1980, 1, 1, 0, 0, 0)
_FIXED_CORE_XML = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\r\n'
    '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
    'xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" '
    'xmlns:dcmitype="http://purl.org/dc/dcmitype/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
    '<dc:title>专项施工方案</dc:title><dc:creator>sfc-synth</dc:creator>'
    '<cp:lastModifiedBy>sfc-synth</cp:lastModifiedBy>'
    '<dcterms:created xsi:type="dcterms:W3CDTF">2026-01-01T00:00:00Z</dcterms:created>'
    '<dcterms:modified xsi:type="dcterms:W3CDTF">2026-01-01T00:00:00Z</dcterms:modified>'
    '</cp:coreProperties>'
).encode("utf-8")
_FIXED_APP_XML = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\r\n'
    '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" '
    'xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVT">'
    '<Application>Microsoft Office Word</Application><AppVersion>16.0000</AppVersion>'
    '</Properties>'
).encode("utf-8")

# ---- 模板池（合法组合，出处见模块 docstring）----
_PARAM_POOLS = (
    {   # 池A：二步三跨，la=1.5（表6.1.1-1：lb=1.05/h1.5/2+0.35 档 la≤2.0）
        "step": 1.5, "long_spacing": 1.5, "cross_spacing": 1.05,
        "wall_tie": "两步三跨", "wall_tie_v": 3.0, "wall_tie_h": 4.5,
    },
    {   # 池B：二步三跨，h=1.8（表6.1.1-1：lb=1.05/h1.8/2+0.35 档 la≤1.8）
        "step": 1.8, "long_spacing": 1.5, "cross_spacing": 1.05,
        "wall_tie": "两步三跨", "wall_tie_v": 3.6, "wall_tie_h": 4.5,
    },
    {   # 池C：三步三跨（表6.1.1-1：lb=1.30/h1.5/2+0.35 档 la=1.8）
        "step": 1.5, "long_spacing": 1.8, "cross_spacing": 1.30,
        "wall_tie": "三步三跨", "wall_tie_v": 4.5, "wall_tie_h": 5.4,
    },
)
_PROJECT_NAMES = (
    "某住宅小区3号楼及地下车库工程",
    "某产业园研发楼项目",
    "某学校改扩建工程教学楼",
)
_STRUCT_TYPES = ("框架结构", "框架剪力墙结构")
_BOARD_LAYERS = (1, 2)
_LIVE_LOAD_TEXT = {
    2.0: "装修作业（施工均布荷载标准值 2.0kN/m²）",
    3.0: "混凝土结构作业（施工均布荷载标准值 3.0kN/m²）",
}

_LIVE_POOLS = ((2.0, 12.0), (2.0, 18.0), (3.0, 18.0))  # (施工荷载, 搭设高度)——落地双排≤50m 合法


def _fmt(x):
    """数值定形：两位小数去尾零（1.05→"1.05"、1.5→"1.5"、56.0→"56"）。

    保留 1.05 的精确档位值（表6.1.1-1 立杆横距档），避免 %.1f 舍入成 1.1。
    """
    s = ("%.2f" % float(x))
    s = s.rstrip("0").rstrip(".")
    return s if s else "0"


def _import_docx():
    try:
        import docx  # noqa: F401
        from docx import Document
        from docx.shared import Pt
        return Document, Pt
    except ImportError as e:
        raise RuntimeError(
            "synth 生成器需要 python-docx：请先 pip install -e \".[parse]\" 或 \".[dev]\""
        ) from e


def _scheme_texts(spec, rng):
    """按 spec + 确定性 RNG 组装方案文本要素。"""
    pool = _PARAM_POOLS[spec["pool"]]
    live, height = _LIVE_POOLS[rng.below(len(_LIVE_POOLS))]
    name = rng.pick(_PROJECT_NAMES)
    struct = rng.pick(_STRUCT_TYPES)
    board_n = rng.pick(_BOARD_LAYERS)
    scheme = {
        "name": name,
        "struct": struct,
        "build_height": height,
        "step": pool["step"],
        "long_spacing": pool["long_spacing"],
        "cross_spacing": pool["cross_spacing"],
        "wall_tie": pool["wall_tie"],
        "wall_tie_v": pool["wall_tie_v"],
        "wall_tie_h": pool["wall_tie_h"],
        "board_layers": board_n,
        "live": live,
        "calc_step": pool["step"],   # 验算书取值（two_sheets 注入时改写）
        "mention_brace": True,
        "mention_expert_review": True,
    }
    inj = spec["injection"]
    if inj == "step_over":
        scheme["step"] = 2.4
        scheme["calc_step"] = 2.4
    elif inj == "walltie_over":
        scheme["wall_tie_v"] = round(pool["wall_tie_v"] * 2.0, 1)  # 4步竖距，必超 3h
    elif inj == "brace_missing":
        scheme["mention_brace"] = False
    elif inj == "two_sheets":
        scheme["calc_step"] = 1.5 if pool["step"] != 1.5 else 1.8
    elif inj == "grading_missing":
        scheme["build_height"] = 56.0
        scheme["mention_expert_review"] = False
    elif inj is not None:
        raise ValueError("unknown injection: %r" % (inj,))
    return scheme


def _truth(scheme, spec):
    """真值：主期望 + also_expect（语义见模块 docstring）。"""
    main = []
    also = []
    inj = spec["injection"]
    if inj == "step_over":
        main.append({"rule_id": "R-step-limit", "check_type": "threshold",
                     "param": "step", "op": "<=", "limit_value": 1.8,
                     "actual": scheme["step"], "verdict": "violation",
                     "clause_ref": "JGJ130-6.1.1"})
        also.append({"rule_id": "R-step-limit-20", "check_type": "threshold",
                     "param": "step", "op": "<=", "limit_value": 2.0,
                     "actual": scheme["step"], "verdict": "violation",
                     "clause_ref": "JGJ130-6.1.1",
                     "note": "2.4m 同时超出表6.1.1-1 全部步距档（最大 2.0m 仅满堂支撑架侧）"})
    elif inj == "walltie_over":
        main.append({"rule_id": "R-walltie-vspacing", "check_type": "threshold",
                     "param": "wall_tie_v", "op": "<=", "limit_value": 3 * 1.8,
                     "actual": scheme["wall_tie_v"], "verdict": "violation",
                     "clause_ref": "JGJ130-6.4.2"})
        area = round(scheme["wall_tie_v"] * scheme["wall_tie_h"], 2)
        if area > 40.0:
            # 仅在真超限时登记 also_expect（评测按"全部非 pass 集合"对账）
            also.append({"rule_id": "R-walltie-area", "check_type": "threshold",
                         "param": "wall_tie_area", "op": "<=", "limit_value": 40.0,
                         "actual": area, "verdict": "violation",
                         "clause_ref": "JGJ130-6.4.2"})
    elif inj == "brace_missing":
        main.append({"rule_id": "R-brace-presence", "check_type": "presence",
                     "param": "scissor_brace", "verdict": "violation",
                     "clause_ref": "JGJ130-6.6.2"})
    elif inj == "two_sheets":
        main.append({"rule_id": "R-consistency-step", "check_type": "consistency",
                     "param": "step", "scheme_value": scheme["step"],
                     "calcbook_value": scheme["calc_step"], "verdict": "violation",
                     "clause_ref": "37号令-第十六条",
                     "note": "方案正文与验算书取值不一致；按影响方向定级（劣于=不合格）"})
    elif inj == "grading_missing":
        main.append({"rule_id": "R-grading-expert-review", "check_type": "grading",
                     "param": "build_height", "level": "chaoguimo",
                     "actual": scheme["build_height"], "verdict": "violation",
                     "clause_ref": "37号令-第十二条",
                     "note": "超过一定规模应专家论证而方案未标注论证安排"})
        also.append({"rule_id": "G-pan-luodi-50", "check_type": "grading",
                     "param": "build_height", "level": "chaoguimo",
                     "actual": scheme["build_height"], "verdict": "triggered",
                     "clause_ref": "pan-luodi-gangguan-24",
                     "note": "危大分级判定=超过一定规模（>=50m）"})
    elif inj is not None:
        raise ValueError("unknown injection: %r" % (inj,))
    return {"fixture_id": spec["id"], "injection": inj or "clean",
            "main_expect": main, "also_expect": also, "clean_baseline": inj is None}


def _docx_bytes(scheme):
    """生成方案 docx 字节（重写 zip 元数据保证无时间戳、字节确定）。"""
    Document, Pt = _import_docx()
    doc = Document()
    style = doc.styles["Normal"]
    style.font.name = "SimSun"
    style.font.size = Pt(12)
    try:
        from docx.oxml.ns import qn
        style.element.rPr.rFonts.set(qn("w:eastAsia"), "宋体")
    except Exception:
        pass  # eastAsia 设置失败不影响确定性

    doc.add_heading("%s 落地式扣件钢管脚手架专项施工方案" % scheme["name"], level=0)

    doc.add_heading("一、工程概况", level=1)
    doc.add_paragraph(
        "本工程为%s，总建筑面积约36000m²。脚手架采用落地式扣件钢管脚手架（双排），"
        "搭设高度%s m，随主体结构逐层搭设。" % (scheme["struct"], _fmt(scheme["build_height"]))
    )

    doc.add_heading("二、编制依据", level=1)
    for line in (
        "《建筑施工扣件式钢管脚手架安全技术规范》JGJ 130-2011",
        "《危险性较大的分部分项工程安全管理规定》（住房和城乡建设部令第37号）",
        "《住房城乡建设部办公厅关于实施〈危险性较大的分部分项工程安全管理规定〉"
        "有关问题的通知》（建办质〔2018〕31号）",
        "本工程施工图设计文件及施工组织设计",
    ):
        doc.add_paragraph(line, style="List Bullet")

    doc.add_heading("三、搭设参数", level=1)
    table = doc.add_table(rows=1, cols=2)
    table.style = "Table Grid"
    hdr = table.rows[0].cells
    hdr[0].text = "参数"
    hdr[1].text = "取值"
    rows = [
        ("立杆横距 lb", "%s m" % _fmt(scheme["cross_spacing"])),
        ("立杆纵距 la", "%s m" % _fmt(scheme["long_spacing"])),
        ("步距 h", "%s m" % _fmt(scheme["step"])),
        ("连墙件布置", scheme["wall_tie"]),
        ("连墙件竖向间距", "%s m" % _fmt(scheme["wall_tie_v"])),
        ("连墙件水平间距", "%s m" % _fmt(scheme["wall_tie_h"])),
        ("钢管规格", "φ48.3×3.6（Q235A）"),
        ("脚手板", "冲压钢脚手板（自重标准值0.30kN/m²），铺%s层" % scheme["board_layers"]),
        ("施工荷载", _LIVE_LOAD_TEXT[scheme["live"]]),
    ]
    for k, v in rows:
        cells = table.add_row().cells
        cells[0].text = k
        cells[1].text = v

    doc.add_heading("四、构造措施", level=1)
    doc.add_paragraph(
        "1. 立杆基础：基础平整夯实，设置垫板与底座，立杆底部设置纵横向扫地杆，"
        "扫地杆固定在距底座上皮不大于200mm处的立杆上。"
    )
    doc.add_paragraph(
        "2. 连墙件：按%s布置，竖向间距%s m、水平间距%s m，靠近主节点设置，"
        "偏离主节点的距离不大于300mm；连墙件采用可承受拉力和压力的刚性构造。"
        % (scheme["wall_tie"], _fmt(scheme["wall_tie_v"]), _fmt(scheme["wall_tie_h"]))
    )
    if scheme["mention_brace"]:
        doc.add_paragraph(
            "3. 剪刀撑：每道剪刀撑跨越立杆5～7根，宽度不小于4跨且不小于6m，"
            "斜杆与地面倾角45°～60°；本工程搭设高度24m及以上（若适用），"
            "外侧全立面连续设置剪刀撑，由底至顶连续布置。"
        )
    doc.add_paragraph(
        "%s. 防护：栏杆与挡脚板齐全，密目式安全立网全封闭围护。"
        % ("4" if scheme["mention_brace"] else "3")
    )

    doc.add_heading("五、危大工程管理", level=1)
    if scheme["build_height"] >= 24.0:
        doc.add_paragraph(
            "本工程搭设高度%s m，达到24m及以上，属危险性较大的分部分项工程"
            "（建办质〔2018〕31号附件1），已编制本专项施工方案，"
            "经施工单位技术负责人审核签字并加盖单位公章、总监理工程师审查签字"
            "并加盖执业印章后实施。" % _fmt(scheme["build_height"])
        )
    else:
        doc.add_paragraph(
            "本工程搭设高度%s m，未达到24m，不属危险性较大的分部分项工程，"
            "按常规安全管理执行。" % _fmt(scheme["build_height"])
        )
    if scheme["build_height"] >= 50.0 and scheme["mention_expert_review"]:
        doc.add_paragraph(
            "本工程搭设高度%s m，达到50m及以上，属超过一定规模的危险性较大的"
            "分部分项工程（建办质〔2018〕31号附件2），实施前已组织专家论证，"
            "专家组人数不少于5名，论证报告结论为通过。" % _fmt(scheme["build_height"])
        )

    doc.add_heading("六、验算书", level=1)
    doc.add_paragraph(
        "立杆稳定性验算取值：步距 %s m，立杆纵距 %s m，立杆横距 %s m。"
        % (_fmt(scheme["calc_step"]), _fmt(scheme["long_spacing"]),
           _fmt(scheme["cross_spacing"]))
    )
    doc.add_paragraph(
        "钢管截面特性按JGJ 130-2011附录B表B.0.1（A=5.06cm²、i=1.59cm、"
        "W=5.26cm³），钢材强度设计值f=205N/mm²（表5.1.6）。"
    )
    doc.add_paragraph(
        "经计算，立杆稳定性满足规范要求（计算过程详见计算书附页）。"
    )

    buf = io.BytesIO()
    doc.save(buf)
    return _normalize_zip(buf.getvalue())


def _normalize_zip(raw):
    """重写 docx zip：固定条目时间戳、覆写 core/app 元数据（无时间戳纪律）。"""
    src = zipfile.ZipFile(io.BytesIO(raw))
    try:
        infos = src.infolist()
        payloads = [(i, src.read(i.filename)) for i in infos]
    finally:
        src.close()
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for info, data in payloads:
            zi = zipfile.ZipInfo(info.filename, date_time=_ZIP_DATE)
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.external_attr = info.external_attr
            if info.filename == "docProps/core.xml":
                data = _FIXED_CORE_XML
            elif info.filename == "docProps/app.xml":
                data = _FIXED_APP_XML
            z.writestr(zi, data)
    return out.getvalue()


def build_fixture_bytes(spec):
    """构建单个 fixture：返回 (docx_bytes, truth_dict)。同 spec 逐字节可复现。"""
    index = FIXTURE_SPECS.index(spec)
    rng = SplitMix64(FIXTURE_SEED + index)
    scheme = _scheme_texts(spec, rng)
    truth = _truth(scheme, spec)
    return _docx_bytes(scheme), truth


FIXTURE_SPECS = (
    {"id": "SY-clean-01", "injection": None, "pool": 0},
    {"id": "SY-clean-02", "injection": None, "pool": 1},
    {"id": "SY-step-over-01", "injection": "step_over", "pool": 0},
    {"id": "SY-step-over-02", "injection": "step_over", "pool": 2},
    {"id": "SY-walltie-over-01", "injection": "walltie_over", "pool": 1},
    {"id": "SY-walltie-over-02", "injection": "walltie_over", "pool": 0},
    {"id": "SY-brace-missing-01", "injection": "brace_missing", "pool": 2},
    {"id": "SY-brace-missing-02", "injection": "brace_missing", "pool": 0},
    {"id": "SY-two-sheets-01", "injection": "two_sheets", "pool": 1},
    {"id": "SY-two-sheets-02", "injection": "two_sheets", "pool": 2},
    {"id": "SY-grading-missing-01", "injection": "grading_missing", "pool": 0},
    {"id": "SY-grading-missing-02", "injection": "grading_missing", "pool": 1},
)


def generate_all(out_dir):
    """生成全部 fixtures（docx + 真值 JSON + manifest）到 out_dir。"""
    import hashlib
    import os

    if not os.path.isdir(out_dir):
        os.makedirs(out_dir)
    manifest = {"seed": FIXTURE_SEED, "fixtures": []}
    for spec in FIXTURE_SPECS:
        docx_bytes, truth = build_fixture_bytes(spec)
        stem = spec["id"]
        docx_path = os.path.join(out_dir, stem + ".docx")
        truth_path = os.path.join(out_dir, stem + ".truth.json")
        with open(docx_path, "wb") as f:
            f.write(docx_bytes)
        with open(truth_path, "w", encoding="utf-8", newline="\n") as f:
            json.dump(truth, f, ensure_ascii=False, indent=2, sort_keys=True)
            f.write("\n")
        manifest["fixtures"].append({
            "id": spec["id"],
            "injection": spec["injection"] or "clean",
            "pool": spec["pool"],
            "docx": stem + ".docx",
            "truth": stem + ".truth.json",
            "docx_sha256": hashlib.sha256(docx_bytes).hexdigest(),
        })
    manifest_path = os.path.join(out_dir, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")
    return manifest
