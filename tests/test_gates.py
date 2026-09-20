#!/usr/bin/env python3
"""闸门一致性测试：SKILL.md 写的数字 = 脚本里执行的数字 = 表里判定的结果。

跑法（不需要 pytest，标准库就够）：
    python3 tests/test_gates.py

这套测试存在的理由：闸门阈值以前抄在 5 个文件里，改一处忘一处，
skill 就会「说一套做一套」。现在数字只有两个来源——SKILL.md ④ 和
scripts/fire_table.py 顶部常量——本文件负责盯着它们不许分家。
"""

import datetime as dt
import importlib.util
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SKILL = ROOT / "viral-copy-forge" / "SKILL.md"

spec = importlib.util.spec_from_file_location(
    "fire_table", ROOT / "viral-copy-forge" / "scripts" / "fire_table.py")
ft = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ft)

FAILED = []


def check(name, ok, detail=""):
    print(("  ok   " if ok else "  FAIL ") + name + (f" — {detail}" if detail and not ok else ""))
    if not ok:
        FAILED.append(name)


def gates_text():
    """截出 SKILL.md ④段「火力闸门」到该段结束的那块正文。"""
    text = SKILL.read_text(encoding="utf-8")
    start = text.index("## 第④段")
    end = text.index("## 第⑤段")
    return text[start:end]


def test_numbers_match_skill():
    """SKILL.md ④ 里写的每个阈值，都要等于脚本常量。"""
    g = gates_text()
    cases = [
        ("爆款线倍数", rf"爆款线 = {ft.BOOM_MULT} × 中位赞"),
        ("平台样本闸", rf"单平台有效样本 <{ft.PLATFORM_MIN_SAMPLE} 条"),
        ("小红书标签最小样本", rf"小红书 ≥{ft.TAG_MIN_SAMPLE['xiaohongshu']} 条"),
        ("抖音标签最小样本", rf"抖音 ≥{ft.TAG_MIN_SAMPLE['douyin']} 条"),
        ("时间衰减天数", rf"近 {ft.DECAY_DAYS} 天"),
        ("离群封顶倍数", rf"{ft.OUTLIER_CAP_MULT} 倍，按 {ft.OUTLIER_CAP_MULT}×中位数"),
        ("单条贡献上限", rf">{int(ft.SINGLE_SHARE_MAX * 100)}%"),
        ("最低门槛倍数", rf"< 类目 {ft.MIN_TOTAL_MULT} 倍中位赞"),
        ("实证档爆款条数", rf"≥{ft.MIN_BOOM_NOTES} 条爆款里的标签为「实证档」"),
        ("无日期降级占比", rf"超过 {int(ft.UNDATED_MAX_SHARE * 100)}% 的有效样本没有发布日期"),
    ]
    for name, pattern in cases:
        check(f"SKILL.md ④ 写的{name}与脚本常量一致",
              re.search(pattern, g) is not None, f"SKILL.md 里找不到 /{pattern}/")


def test_no_stale_numbers_elsewhere():
    """其他文档不得再自己抄一遍阈值——只许指回 SKILL.md ④。"""
    stale = {
        "小红书 ≥8 条": "标签最小样本闸",
        "抖音 ≥5 条视频": "标签最小样本闸",
        "有效样本 <20 条": "平台样本闸",
        "10×中位数计入": "离群封顶",
    }
    others = [p for p in ROOT.rglob("*.md")
              if p != SKILL and ".git" not in p.parts and "examples" not in p.parts]
    for phrase, gate in stale.items():
        hits = [str(p.relative_to(ROOT)) for p in others if phrase in p.read_text(encoding="utf-8")]
        check(f"{gate}的数字没有被别处重抄（「{phrase}」）", not hits, "出现在 " + ", ".join(hits))


def test_template_has_no_real_numbers():
    """模板页不许带真赞数——模型会照抄成别的产品的「证据」。

    2026-09-19 盲评实测：copy-package.md 里的示范数字（9,725 赞、约 181.8 万赞）
    被写手原样抄进了防脱、猫粮两份不相干的交付物，当成本产品的证据。
    所以模板里的数字位一律写占位符，真数字只能来自本轮火力表。
    """
    tpl = ROOT / "viral-copy-forge" / "templates" / "copy-package.md"
    text = tpl.read_text(encoding="utf-8")
    nums = re.findall(r"[0-9][0-9,\.]*\s*万?\s*赞", text)
    check("copy-package.md 里没有具体赞数", not nums, "还留着 " + "、".join(nums))
    check("copy-package.md 用了占位符", "〔赞数·占位〕" in text)
    fire = (ROOT / "viral-copy-forge" / "templates" / "fire-table.md").read_text(encoding="utf-8")
    check("fire-table.md 声明了自己的数字只是示范", "只作格式示范" in fire)
    skill = SKILL.read_text(encoding="utf-8")
    check("SKILL ⑤ 有闸〇 声明落地", "闸〇 · 声明落地" in skill)
    check("闸〇 排在闸一前面", skill.index("闸〇 · 声明落地") < skill.index("闸一 · 锚点与刺点"))


def rows(spec_rows, platform="xiaohongshu"):
    out = []
    for i, (likes, tags, days_ago) in enumerate(spec_rows):
        out.append({"id": f"n{i}", "title": f"第{i}条", "likes": likes, "tags": tags,
                    "url": f"https://example.invalid/{i}",
                    "published_at": (dt.date(2026, 9, 19) - dt.timedelta(days=days_ago)).isoformat()})
    return {"platform": platform, "collected_at": "2026-09-19", "rows": out}


ASOF = dt.date(2026, 9, 19)


def test_gate_behaviour():
    """每道闸都用一份最小数据实际跑一遍，确认它真的挡住了东西。"""
    # 平台样本闸：19 条 → 观察级；20 条 → 实测级
    small = ft.analyse(rows([(100, ["#a"], 1)] * 19), ASOF)
    big = ft.analyse(rows([(100, ["#a"], 1)] * 20), ASOF)
    check("样本 19 条判观察级", small["level"] == "观察级", small["level"])
    check("样本 20 条判实测级", big["level"] == "实测级", big["level"])

    # 无日期降级闸：过半样本没有发布日期 → 即便够 20 条也只能是观察级
    undated = rows([(100, ["#a"], 1)] * 20)
    for r in undated["rows"][:11]:
        r["published_at"] = None
    half = ft.analyse(undated, ASOF)
    check("过半样本无日期判观察级", half["level"] == "观察级", half["level"])
    undated2 = rows([(100, ["#a"], 1)] * 20)
    for r in undated2["rows"][:10]:
        r["published_at"] = None
    check("恰好一半无日期仍判实测级",
          ft.analyse(undated2, ASOF)["level"] == "实测级",
          ft.analyse(undated2, ASOF)["level"])

    # 观察级下档位写「观察·实证」，不许出现光秃秃的「实证」
    md = ft.render(ft.analyse(rows([(100, ["#a"], 1)] * 10 + [(1000, ["#a"], 1)] * 9), ASOF))
    check("观察级表里档位写「观察·」前缀", "| 观察·" in md or "| —— |" in md, md.splitlines()[6])

    # 90 天衰减闸：91 天前的爆款不计入
    r = ft.analyse(rows([(100, ["#a"], 1)] * 20 + [(9999, ["#old"], 91)]), ASOF)
    check("超 90 天的样本被剔除", r["dropped"] == 1 and all(t["tag"] != "#old" for t in r["tags"]))

    # 缺赞记 null 不当 0
    data = rows([(100, ["#a"], 1)] * 20)
    data["rows"].append({"id": "x", "title": "没赞", "likes": None, "tags": ["#a"],
                         "published_at": "2026-09-18"})
    check("likes 为 null 的行被剔除而不是按 0 计入", ft.analyse(data, ASOF)["sample"] == 20)

    # 离群封顶 + 单条贡献闸
    data = rows([(100, ["#a"], 1)] * 19 + [(100000, ["#a"], 1)])
    r = ft.analyse(data, ASOF)
    tag = next(t for t in r["tags"] if t["tag"] == "#a")
    check("单条超 10×中位的赞按封顶计入", tag["total"] == int(ft.OUTLIER_CAP_MULT * r["median"]),
          f"total={tag['total']} cap={r['cap']}")
    check("单条贡献 >70% 的标签被挡出主表",
          any("单条贡献" in reason for reason in tag["blocked_by"]), tag["blocked_by"])

    # 标签最小样本闸：小红书 7 条 → 挡住；8 条 → 放行
    def tag_row(n):
        data = rows([(100, ["#b"], 1)] * 12 + [(1000, ["#a"], 1)] * n)
        return next(t for t in ft.analyse(data, ASOF)["tags"] if t["tag"] == "#a")
    below = tag_row(ft.TAG_MIN_SAMPLE["xiaohongshu"] - 1)
    at = tag_row(ft.TAG_MIN_SAMPLE["xiaohongshu"])
    check("含该标签 7 条被挡进弱证据附录",
          any("最小" in x or "< 8" in x or "样本" in x for x in below["blocked_by"]), below["blocked_by"])
    check("含该标签 8 条可进主表", not at["blocked_by"], at["blocked_by"])

    # 档位：2 条爆款为实证，1 条为孤证
    data = rows([(100, ["#b"], 1)] * 12 + [(1000, ["#a"], 1)] + [(100, ["#a"], 1)] * 7)
    t = next(x for x in ft.analyse(data, ASOF)["tags"] if x["tag"] == "#a")
    check("只有 1 条爆款判孤证档", t["tier"] == "孤证", t["tier"])

    # 抖音闸门数字与小红书不同，且确实生效
    dy = rows([(100, ["#b"], 1)] * 16 + [(1000, ["#a"], 1)] * 4, platform="douyin")
    t = next(x for x in ft.analyse(dy, ASOF)["tags"] if x["tag"] == "#a")
    check("抖音 4 条被挡（阈值 5 条）", bool(t["blocked_by"]), t["blocked_by"])


def test_examples_still_reproduce():
    """仓库里的示例输出必须能被示例数据重新跑出来。"""
    out = ROOT / "examples" / "out" / "fire-table-2026-09-19.md"
    if not out.exists():
        check("示例输出存在", False, str(out))
        return
    files = [ROOT / "examples" / "data" / "xhs-2026-09-19.json",
             ROOT / "examples" / "data" / "douyin-2026-09-19.json"]
    fresh = "\n\n".join(ft.render(ft.analyse(ft.load(str(f)), ASOF)) for f in files)
    check("examples/out 与示例数据一致（改了算法记得重跑）",
          fresh.strip() == out.read_text(encoding="utf-8").strip())


if __name__ == "__main__":
    print("闸门一致性测试")
    for fn in (test_numbers_match_skill, test_no_stale_numbers_elsewhere,
               test_template_has_no_real_numbers,
               test_gate_behaviour, test_examples_still_reproduce):
        print(f"\n{fn.__doc__.splitlines()[0]}")
        fn()
    print()
    if FAILED:
        print(f"{len(FAILED)} 项未通过：" + "；".join(FAILED))
        sys.exit(1)
    print("全部通过。")
