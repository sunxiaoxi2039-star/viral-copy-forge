#!/usr/bin/env python3
"""出厂扫描测试：python3 tests/test_lint.py

只用标准库。确认 lint_package.py 既挡得住真违规，也不把合规段自己的用词判死。
"""

import importlib.util
import pathlib
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
LINT = ROOT / "viral-copy-forge" / "scripts" / "lint_package.py"
spec = importlib.util.spec_from_file_location("lint_package", LINT)
lint = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lint)

FAILED = []


def check(name, ok, detail=""):
    print(f"  {'ok  ' if ok else 'FAIL'} {name}" + (f"　← {detail}" if not ok and detail else ""))
    if not ok:
        FAILED.append(name)


GOOD = """# 文案包

## 标题
标题：第 28 天，我把每周一张的照片排了出来（主推）

## 正文
> 发缝变宽的第 3 年，我开始每周拍一张头顶。

## 证据行
| 文案位 | 证据 |
|---|---|
| 标题 | 1,138 赞 |

## 合规警示
不宣称生发、不宣称治疗脱发；严重掉发指向医院。

## 闸门通过记录
单条贡献 100%，只借结构。

## 数据缺口声明
抖音只有 20 条。

## 丑话三句
点赞不等于转化。
"""


def run(text, *args):
    with tempfile.NamedTemporaryFile("w", suffix=".md", encoding="utf-8", delete=False) as f:
        f.write(text)
        path = f.name
    p = subprocess.run([sys.executable, str(LINT), path, *args],
                       capture_output=True, text=True)
    return p.returncode, p.stdout


def main():
    print("出厂扫描测试\n")

    print("一份干净的包应当零硬伤。")
    code, out = run(GOOD)
    check("合规的包退出码 0", code == 0, out)
    check("合规段里的「不宣称生发」不判死", "医疗越线（合规 §2）：" not in out, out)
    check("审计段里的「100%」不判死", "极限词（合规 §1）：" not in out, out)

    print("\n真违规必须判死。")
    code, out = run(GOOD.replace("> 发缝变宽的第 3 年", "> 亲测有效，闭眼入，第 3 年"))
    check("正文里的黑名单词判硬伤", code == 1 and "万能补丁黑名单" in out, out)

    code, out = run(GOOD.replace("> 发缝变宽的第 3 年", "> 这瓶能生发，第 3 年"))
    check("正文里裸用医疗词判硬伤", code == 1 and "医疗越线" in out, out)

    code, out = run(GOOD.replace("> 发缝变宽的第 3 年", "> 加微信领券，第 3 年"))
    check("站外导流判硬伤", code == 1 and "站外导流" in out, out)

    code, out = run(GOOD.replace("> 发缝变宽的第 3 年", "> 全网都在用，第 3 年"),
                    "--single-platform", "xiaohongshu")
    check("单平台证据用跨平台措辞判硬伤", code == 1 and "跨平台" in out, out)

    code, out = run(GOOD.replace("> 发缝变宽的第 3 年", "> 这是实测最火的标签，第 3 年"),
                    "--observational")
    check("观察级却宣称实证判硬伤", code == 1 and "观察级" in out, out)

    print("\n交付五件套缺一不可。")
    code, out = run(GOOD.replace("## 丑话三句\n点赞不等于转化。\n", ""))
    check("缺丑话三句判硬伤", code == 1 and "丑话三句" in out, out)

    code, out = run(GOOD.replace("（主推）", ""))
    check("没标主推判硬伤", code == 1 and "主推" in out, out)

    code, out = run(GOOD.replace("标题：第 28 天，我把每周一张的照片排了出来（主推）",
                                 "标题：我把照片排了出来（主推）"))
    check("标题缺锚点判硬伤", code == 1 and "锚点" in out, out)

    print("\n⑤闸〇 声明落地：台账驳回的说法不许进文案。")
    ledger = "\n## Claim Ledger\n| 声明 | 来源 | 证据 | 判定 |\n|---|---|---|---|\n| 5% 米诺地尔 | 客服口述 | 无备案 | 驳回 |\n"
    code, out = run(GOOD.replace("## 合规警示", ledger + "\n## 合规警示")
                        .replace("标题：第 28 天，", "标题：5% 米诺地尔，第 28 天，"))
    check("驳回的说法进了标题判硬伤", code == 1 and "闸〇" in out, out)

    code, out = run(GOOD.replace("## 合规警示\n不宣称生发",
                                 ledger + "\n## 合规警示\n「5% 米诺地尔」无备案不可用；不宣称生发"))
    check("驳回的说法只留在合规段不判死", code == 0, out)

    ledger2 = "\n## Claim Ledger\n- #1：「39℃恒温发热科技，比普通棉暖3倍」→ 厂家宣传语 → 状态：待补\n"
    code, out = run(GOOD.replace("## 合规警示", ledger2 + "\n## 合规警示")
                        .replace("标题：第 28 天，", "标题：39℃恒温科技，第 28 天，"))
    check("长句声明被改头换面，数字卖点照样判硬伤", code == 1 and "「39℃」" in out, out)
    ledger3 = "\n## Claim Ledger\n| 5% 米诺地尔 | 客服口述 | 无备案 | 驳回 |\n"
    code, out = run(GOOD.replace("## 合规警示", ledger3 + "\n## 合规警示")
                        .replace("标题：第 28 天，", "标题：95%的人没注意，第 28 天，"))
    check("「95%」不算撞上被驳回的「5%」", "闸〇" not in out, out)
    code, out = run(GOOD.replace("## 合规警示\n不宣称生发", "## 合规警示\n「39℃恒温发热科技」为厂家宣传语，无检测报告背书；不宣称生发")
                        .replace("标题：第 28 天，", "标题：39℃恒温，第 28 天，"))
    check("台账换了措辞（宣传语／无检测报告）也算驳回", code == 1 and "闸〇" in out, out)
    tl = lint.title_lines("### 标题主推\n**「领口无骨缝，一穿就喊软」｜穿了 3 天不扎了**\n")
    check("「前半」｜后半 的标题，后半也算进标题", tl and "3 天" in tl[0], tl)

    code, out = run(GOOD.replace("1,138 赞", "〔赞数·占位〕"))
    check("占位符抄进交付物判硬伤", code == 1 and "占位符" in out, out)
    code, out = run(GOOD.replace("标题：第 28 天，", "标题：本例为教学示范，第 28 天，"))
    check("教学注解抄进交付物判硬伤", code == 1 and "教学注解" in out, out)

    code, out = run(GOOD.replace("| 标题 | 1,138 赞 |", "| 标题 | 9,725 赞 |"))
    check("抄模板示范赞数判硬伤", code == 1 and "示范赞数" in out, out)

    with tempfile.NamedTemporaryFile("w", suffix=".md", encoding="utf-8", delete=False) as f:
        f.write("| #防脱 | 3 条爆款／加权赞 4,000 | 实证 | [某条 1,138 赞](x) |")
        table = f.name
    code, out = run(GOOD, "--fire-table", table)
    check("赞数在本轮火力表里就放行", code == 0, out)
    code, out = run(GOOD.replace("1,138 赞", "8,801 赞"), "--fire-table", table)
    check("赞数指不回本轮材料判硬伤", code == 1 and "指不回" in out, out)

    with tempfile.NamedTemporaryFile("w", suffix=".md", encoding="utf-8", delete=False) as f:
        f.write("| xiaohongshu | 某条真笔记 | 8801 | 2026-05-12 | #防脱 | https://x |")
        samples = f.name
    code, out = run(GOOD.replace("1,138 赞", "8,801 赞"), "--fire-table", table, samples)
    check("证据行引用本轮样本表里的真笔记赞数就放行", code == 0, out)

    with tempfile.NamedTemporaryFile("w", suffix=".md", encoding="utf-8", delete=False) as f:
        f.write("| #防脱 | 3 条爆款／加权赞 1,138／样本 9 条 | 实证 |")
        table2 = f.name
    code, out = run(GOOD, "--fire-table", table2)
    check("火力表把「赞」写在数字前面也算指得回", code == 0, out)

    code, out = run(GOOD.replace("1,138 赞", "1138 赞"), "--fire-table", table)
    check("同一个数字漏写千分位也算指得回", code == 0, out)

    print("\n9-21 修的误判与新闸：序数、书名号、批注、照抄模板、标题识别、行号。")
    code, out = run(GOOD.replace("发缝变宽的第 3 年", "第一次发现发缝变宽"))
    check("「第一次」是序数，不算极限词", code == 0, out)
    code, out = run(GOOD.replace("发缝变宽的第 3 年", "全城第一名的发缝"))
    check("「第一名」仍然判极限词", code == 1 and "第一" in out, out)
    code, out = run(GOOD.replace("发缝变宽的第 3 年", "长出第一缕绒毛"))
    check("「第一缕」是序数修辞，不算极限词", code == 0, out)
    code, out = run(GOOD.replace("> 发缝变宽的第 3 年，我开始每周拍一张头顶。",
                                 "> 那篇《只认100%纯棉真的不够》我也看过。"))
    check("书名号里引的别人标题不算极限词", code == 0, out)
    code, out = run(GOOD.replace("每周拍一张头顶。", "每周拍一张头顶（A，痛点具象 1,138 赞）。"))
    check("正文夹写法批注判硬伤", code == 1 and "写法批注" in out, out)
    code, out = run(GOOD.replace("每周拍一张头顶。", "每周拍一张头顶（真的）。"))
    check("普通口语括号不算批注", code == 0, out)
    sample = [t for t in lint.template_sentences() if len(t) >= 8][0]
    code, out = run(GOOD.replace("我开始每周拍一张头顶", sample))
    check("照抄模板示范句判硬伤", code == 1 and "示范句" in out, out)
    check("模板示范句里不再夹批注", all("（" not in t for t in lint.template_sentences()))
    main_title = GOOD.replace("## 标题\n标题：第 28 天，我把每周一张的照片排了出来（主推）",
                              "## 标题主推\n**「我把照片排了出来给你们看」**")
    code, out = run(main_title)
    check("「」写法的主推标题也查锚点", code == 1 and "标题缺锚点" in out, out)
    code, out = run(main_title.replace("「我把", "「第 28 天，我把") + "\n## 备选留档\n1. 「换个角度写写看吧」\n")
    check("备选留档不查锚点", code == 0, out)
    code, out = run(GOOD.replace("我开始每周拍一张头顶", "我开始用全网最好的精华"))
    check("硬伤带行号", "第 7 行" in out, out)

    print("\n分段函数本身。")
    copy_text, audit_text = lint.split_audit(GOOD)
    check("合规警示被划进审计段", "不宣称生发" in audit_text and "不宣称生发" not in copy_text)
    check("正文留在文案段", "发缝变宽的第 3 年" in copy_text)

    print("\n" + ("全部通过。" if not FAILED else f"{len(FAILED)} 项未通过：" + "、".join(FAILED)))
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
