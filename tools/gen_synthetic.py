# -*- coding: utf-8 -*-
"""生成 data/synthetic/ 冻结 fixtures（M1-5 演示物）。

纪律：
- 固定 seed（FIXTURE_SEED），两次运行位级一致（tests/test_synth_freeze.py 守门）；
- data/synthetic/ 禁止手改；改体例/生成器 → 用本命令重新生成整目录提交；
- 落盘无时间戳（docx zip 元数据固定值覆写）。

用法: py -X utf8 tools/gen_synthetic.py [--check]
  --check: 只复算比对不写文件（生成到临时目录与仓库 fixtures 逐字节比对，退出码 0=一致）
"""
import sys

from scaffold_formwork_checker.synth import generate_all


def main(argv):
    if "--check" in argv:
        import filecmp
        import os
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            generate_all(td)
            repo = os.path.join("data", "synthetic")
            names = sorted(os.listdir(td))
            diff = []
            for name in names:
                a = os.path.join(td, name)
                b = os.path.join(repo, name)
                if not os.path.exists(b) or not filecmp.cmp(a, b, shallow=False):
                    diff.append(name)
            if diff:
                print("MISMATCH %d 个文件（改体例须重新生成整目录提交）:" % len(diff))
                for n in diff:
                    print("  -", n)
                return 1
            print("FROZEN_FIXTURES_OK %d 个文件位级一致" % len(names))
            return 0
    manifest = generate_all("data/synthetic")
    print("SYNTHETIC_FIXTURES_GENERATED %d 个" % len(manifest["fixtures"]))
    for fx in manifest["fixtures"]:
        print("  %-24s %-16s pool=%d sha256=%s" % (
            fx["id"], fx["injection"], fx["pool"], fx["docx_sha256"][:16]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
