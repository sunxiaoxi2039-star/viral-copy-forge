#!/usr/bin/env python3
"""标签火力表计算器（SKILL.md 第④段的规则实现）。

用法：
    python3 scripts/fire_table.py data/xhs.json data/douyin.json
    python3 scripts/fire_table.py data/xhs.json --json out.json

输入：一个或多个 JSON 文件，格式见 docs/DATA_SCHEMA.md。
输出：markdown 火力表（主表 + 弱证据附录），闸门判定全部写在表里。

闸门阈值是 SKILL.md ④ 的数字，本文件是唯一的代码实现；
tests/test_gates.py 会核对两边一致，改一边不改另一边会测试失败。
"""

import argparse
import datetime as dt
import json
import re
import statistics
import sys

# ---- 闸门阈值（与 SKILL.md ④ 闸门表一一对应，勿各自改动）----
BOOM_MULT = 3           # 爆款线 = 3 × 中位赞
PLATFORM_MIN_SAMPLE = 20  # 单平台有效样本 <20 → 整表观察级
UNDATED_MAX_SHARE = 0.50  # 无发布日期的样本占比 >50% → 衰减闸失效，整表观察级
TAG_MIN_SAMPLE = {        # 主火力标签的最小样本（含该标签的条数）
    "xiaohongshu": 8,
    "douyin": 5,
}
DECAY_DAYS = 90         # 只计近 90 天互动
OUTLIER_CAP_MULT = 10   # 单条赞 > 10×中位 → 按 10×中位计入累计
SINGLE_SHARE_MAX = 0.70  # 单条贡献 >70% → 不得标品类主火力
MIN_TOTAL_MULT = 2      # 标签累计赞 < 2×中位 → 只进备选池
MIN_BOOM_NOTES = 2      # ≥2 条爆款为实证档，1 条为孤证档

PLATFORM_CN = {"xiaohongshu": "小红书", "douyin": "抖音"}
TAG_RE = re.compile(r"#([^#\s,，。！!？?]+)")


def norm_tag(tag):
    """标签归一：去掉井号、空白、尾部标点，统一小写。"""
    return "#" + tag.lstrip("#").strip().strip("！!？?。，,").lower()


def load(path):
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    if "platform" not in data or "rows" not in data:
        sys.exit(f"{path}: 缺 platform 或 rows 字段，见 docs/DATA_SCHEMA.md")
    if data["platform"] not in TAG_MIN_SAMPLE:
        sys.exit(f"{path}: platform 只能是 {list(TAG_MIN_SAMPLE)}")
    return data


def row_tags(row):
    """标签来源：tags 字段优先，没有就从正文/标题里抽 #标签。"""
    tags = [norm_tag(t) for t in row.get("tags") or []]
    if not tags:
        text = (row.get("text") or "") + " " + (row.get("title") or "")
        tags = [norm_tag(t) for t in TAG_RE.findall(text)]
    seen, out = set(), []
    for t in tags:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out


def in_window(row, asof):
    """90 天衰减闸：没有日期的行按「日期未知」计入，并在表里标注。"""
    date = row.get("published_at")
    if not date:
        return True, True  # 计入, 日期未知
    try:
        days = (asof - dt.date.fromisoformat(date[:10])).days
    except ValueError:
        return True, True
    return days <= DECAY_DAYS, False


def analyse(data, asof):
    platform = data["platform"]
    kept, dropped, undated = [], 0, 0
    for row in data["rows"]:
        if row.get("likes") is None:      # 缺赞记 null，不当 0
            dropped += 1
            continue
        ok, unknown = in_window(row, asof)
        if not ok:
            dropped += 1
            continue
        undated += bool(unknown)
        kept.append(row)

    if not kept:
        sys.exit(f"{platform}: 90 天窗口内没有带赞样本")

    likes = [int(r["likes"]) for r in kept]
    median = statistics.median(likes)
    cap = OUTLIER_CAP_MULT * median
    boom_line = BOOM_MULT * median
    booms = [r for r in kept if int(r["likes"]) >= boom_line]

    stats = {}
    for row in kept:
        is_boom = int(row["likes"]) >= boom_line
        capped = min(int(row["likes"]), cap)
        for tag in row_tags(row):
            s = stats.setdefault(tag, {"sample": 0, "booms": [], "total": 0.0, "top": 0.0, "dates": []})
            s["sample"] += 1
            if row.get("published_at"):
                s["dates"].append(row["published_at"][:10])
            if is_boom:
                s["booms"].append(row)
                s["total"] += capped
                s["top"] = max(s["top"], capped)

    min_sample = TAG_MIN_SAMPLE[platform]
    rows_out = []
    for tag, s in stats.items():
        if not s["booms"]:
            continue
        share = s["top"] / s["total"] if s["total"] else 0.0
        reasons = []
        if s["sample"] < min_sample:
            reasons.append(f"含该标签样本 {s['sample']} 条 < {min_sample} 条")
        if s["total"] < MIN_TOTAL_MULT * median:
            reasons.append(f"累计赞 {int(s['total']):,} < {MIN_TOTAL_MULT}×中位（{int(MIN_TOTAL_MULT * median):,}）")
        if share > SINGLE_SHARE_MAX:
            reasons.append(f"单条贡献 {share:.0%} > {SINGLE_SHARE_MAX:.0%}：只借结构不借权重")
        rows_out.append({
            "tag": tag,
            "sample": s["sample"],
            "booms": len(s["booms"]),
            "total": int(s["total"]),
            "share": round(share, 3),
            "last_seen": max(s["dates"]) if s["dates"] else None,
            "tier": "实证" if len(s["booms"]) >= MIN_BOOM_NOTES else "孤证",
            "blocked_by": reasons,
            "evidence": [
                {"title": r.get("title") or (r.get("text") or "")[:24],
                 "likes": int(r["likes"]),
                 "url": r.get("url"),
                 "published_at": r.get("published_at")}
                for r in sorted(s["booms"], key=lambda r: -int(r["likes"]))[:3]
            ],
        })
    rows_out.sort(key=lambda r: -r["total"])

    return {
        "platform": platform,
        "collected_at": data.get("collected_at"),
        "queries": data.get("query") or data.get("queries"),
        "sample": len(kept),
        "dropped": dropped,
        "undated": undated,
        "median": median,
        "boom_line": boom_line,
        "cap": cap,
        "booms": len(booms),
        "level": "观察级" if (len(kept) < PLATFORM_MIN_SAMPLE
                              or (kept and undated / len(kept) > UNDATED_MAX_SHARE)) else "实测级",
        "date_range": [min((r.get("published_at") or "")[:10] for r in kept if r.get("published_at")),
                       max((r.get("published_at") or "")[:10] for r in kept if r.get("published_at"))]
        if any(r.get("published_at") for r in kept) else None,
        "tags": rows_out,
    }


def render(result, max_weak=12):
    p = PLATFORM_CN[result["platform"]]
    rng = "～".join(result["date_range"]) if result["date_range"] else "日期未知"
    head = (f"> 火力表 · {p} · 样本 {result['sample']} 条 · {rng} · 仅 likes 口径 · "
            f"**{result['level']}**（中位赞 {int(result['median']):,}／爆款线 {int(result['boom_line']):,}／"
            f"离群封顶 {int(result['cap']):,}／爆款 {result['booms']} 条）")
    obs = result["level"] == "观察级"
    reason = []
    if result["sample"] < PLATFORM_MIN_SAMPLE:
        reason.append(f"有效样本 {result['sample']} 条 < {PLATFORM_MIN_SAMPLE} 条")
    if result["sample"] and result["undated"] / result["sample"] > UNDATED_MAX_SHARE:
        reason.append(f"{result['undated']}/{result['sample']} 条无发布日期，衰减闸失效")
    note = ("\n\n整表为观察级（" + "；".join(reason) + "）：档位一律写「观察·实证／观察·孤证」，"
            "交付物禁用「实测最火」类表述。" if obs else "")

    main, weak = [], []
    for t in result["tags"]:
        tier = ("观察·" + t["tier"]) if obs else t["tier"]
        ev = "；".join(
            (f"[{e['title'][:16]} {e['likes']:,} 赞]({e['url']})" if e.get("url")
             else f"{e['title'][:16]} {e['likes']:,} 赞（无链接，⑥段「来源可点」会否决）")
            for e in t["evidence"])
        if t["blocked_by"]:
            weak.append(f"| {t['tag']} | {t['booms']} 条爆款／加权赞 {t['total']:,}／样本 {t['sample']} 条｜{ev} | "
                        f"{'；'.join(t['blocked_by'])} |")
        else:
            main.append(f"| {t['tag']} | {t['booms']} 条爆款／加权赞 {t['total']:,}／样本 {t['sample']} 条／"
                        f"最近实证 {t['last_seen'] or '未知'} | {tier} | {ev} |")

    out = [head + note, "", "**主表**（过全部闸门，可做⑤段主钩子）：", "",
           "| 标签 | 火力证据 | 档位 | 指回来源 |", "|---|---|---|---|"]
    out += main or ["| —— | 本轮没有标签同时过三道闸 | —— | —— |"]
    out += ["", "**弱证据附录**（禁当主钩子，只可借结构，见闸四）：", "",
            "| 标签 | 证据 | 不能做主钩子的原因 |", "|---|---|---|"]
    out += weak[:max_weak] or ["| —— | —— | —— |"]
    if len(weak) > max_weak:
        out += ["", f"另有 {len(weak) - max_weak} 条更弱的证据已省略（--max-weak 可调）。"]
    out += ["",
            f"口径：加权赞只累计爆款条（≥{int(result['boom_line']):,} 赞），"
            f"单条最多按离群封顶 {int(result['cap']):,} 计，防一条千万赞的视频把整张表带偏。"]
    if result["dropped"]:
        out += [f"剔除 {result['dropped']} 条：超 {DECAY_DAYS} 天或无赞数（缺赞记 null，不当 0）。"]
    if result["undated"]:
        out += [f"{result['undated']} 条无发布日期，已计入但 90 天衰减闸对这些条失效。"]
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description="标签火力表计算器（SKILL.md ④ 的规则实现）")
    ap.add_argument("files", nargs="+", help="采集数据 JSON，格式见 docs/DATA_SCHEMA.md")
    ap.add_argument("--asof", default=dt.date.today().isoformat(), help="计算基准日，默认今天")
    ap.add_argument("--json", help="同时把结构化结果写到这个文件")
    ap.add_argument("--max-weak", type=int, default=12, help="弱证据附录最多列几行，默认 12")
    args = ap.parse_args()

    asof = dt.date.fromisoformat(args.asof)
    results = [analyse(load(f), asof) for f in args.files]
    print("\n\n".join(render(r, args.max_weak) for r in results))
    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(results, fh, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
