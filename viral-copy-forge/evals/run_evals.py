#!/usr/bin/env python3
"""evals 运行器。

它不评分，也不调模型——本仓不带 API key，花钱的动作一律先问人。
它做三件老实事：
1. 把用例的 prompt 和断言清单打出来，让你（或一个模型）照着跑；
2. 你产出文案包后，用 --package 把包交给 scripts/lint_package.py，
   机器能判死的部分自动判，退出码跟着硬伤走；
3. 把机器判不了的断言原样列成待人工项，不假装通过。

用法：
    python3 evals/run_evals.py                                  # 列全部用例
    python3 evals/run_evals.py --case case1-mandi-anti-hairloss # 看单个用例
    python3 evals/run_evals.py --case case1-mandi-anti-hairloss \
        --package out/包.md --single-platform xiaohongshu --observational

退出码：0 = 没有机器可判的硬伤（不等于用例通过），1 = 有硬伤或用例不存在。
"""

import argparse
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
EVALS = os.path.join(HERE, "evals.json")
LINT = os.path.join(os.path.dirname(HERE), "scripts", "lint_package.py")


def load():
    with open(EVALS, encoding="utf-8") as f:
        return json.load(f)["evals"]


def show(case, verbose=True):
    trig = "应触发" if case.get("should_trigger", True) else "不应触发"
    print(f"## {case['id']}　{case['name']}　（{trig}）")
    print(f"\nPrompt：{case['prompt']}")
    if not verbose:
        return
    print("\n断言（人工或模型逐条判）：")
    for i, a in enumerate(case.get("assertions", []), 1):
        print(f"  {i}. ☐ {a}")


def run_lint(package, single_platform=None, observational=False):
    cmd = [sys.executable, LINT, package]
    if single_platform:
        cmd += ["--single-platform", single_platform]
    if observational:
        cmd.append("--observational")
    print(f"\n--- 机器判：{os.path.relpath(LINT)} {os.path.basename(package)} ---")
    sys.stdout.flush()  # 子进程直接写 fd 1，父进程先把缓冲刷掉，免得输出串位
    return subprocess.call(cmd)


def main():
    ap = argparse.ArgumentParser(description="viral-copy-forge evals 运行器")
    ap.add_argument("--case", help="只看某一个用例 id")
    ap.add_argument("--package", help="已产出的文案包文件，交给 lint_package.py 扫")
    ap.add_argument("--single-platform", choices=["xiaohongshu", "douyin"],
                    help="证据只来自单平台时传，透传给 lint_package.py")
    ap.add_argument("--observational", action="store_true",
                    help="火力表是观察级时传，透传给 lint_package.py")
    args = ap.parse_args()

    cases = load()
    if args.case:
        hit = [c for c in cases if c["id"] == args.case]
        if not hit:
            print(f"没有这个用例：{args.case}", file=sys.stderr)
            print("现有：" + "、".join(c["id"] for c in cases), file=sys.stderr)
            return 1
        cases = hit

    print(f"# viral-copy-forge evals（{len(cases)} 个用例）\n")
    for c in cases:
        show(c)
        print()

    if not args.package:
        print("没传 --package，只列清单。产出文案包后加 --package <文件> 让机器判一遍。")
        return 0

    code = run_lint(args.package, args.single_platform, args.observational)
    print("\n注意：退出码只代表机器可判项。上面带 ☐ 的断言仍需人或模型逐条过。")
    return code


if __name__ == "__main__":
    sys.exit(main())
