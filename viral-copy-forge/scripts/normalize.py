#!/usr/bin/env python3
"""把采集器导出的 CSV/JSON 转成 docs/DATA_SCHEMA.md 约定的格式。

用法：
    python3 scripts/normalize.py 采集.csv --platform xiaohongshu -o xhs.json
    python3 scripts/normalize.py 采集.json --platform douyin --likes-field digg_count -o dy.json

字段名对不上时用 --xxx-field 指定，或者先改表头。
「1.2万」这类中文缩写会被还原成整数；空值转成 null（不当 0）。
"""

import argparse
import csv
import datetime as dt
import json
import re
import sys

CN_UNITS = {"万": 10000, "w": 10000, "W": 10000, "k": 1000, "K": 1000, "亿": 100000000}
DEFAULTS = {"likes": ["likes", "like_count", "digg_count", "点赞", "赞"],
            "title": ["title", "desc", "标题", "文案"],
            "url": ["url", "link", "链接"],
            "published_at": ["published_at", "publish_time", "date", "日期", "发布时间"],
            "author": ["author", "nickname", "作者"],
            "tags": ["tags", "hashtags", "标签", "话题"],
            "text": ["text", "content", "正文"],
            "id": ["id", "note_id", "aweme_id"]}


def to_int(value):
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return int(value)
    s = str(value).strip().replace(",", "")
    if not s or s in {"null", "None", "-", "—"}:
        return None
    m = re.match(r"^([\d.]+)\s*([万wWkK亿])?$", s)
    if not m:
        return None
    n = float(m.group(1))
    if m.group(2):
        n *= CN_UNITS[m.group(2)]
    return int(n)


def to_date(value):
    if not value:
        return None
    s = str(value).strip()
    m = re.search(r"(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})", s)
    if m:
        return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    if re.match(r"^\d{9,}$", s):  # 秒级/毫秒级时间戳
        ts = int(s[:10])
        return dt.date.fromtimestamp(ts).isoformat()
    return None


def to_tags(value):
    if not value:
        return []
    if isinstance(value, list):
        items = value
    else:
        items = re.split(r"[,，;；\s]+", str(value))
    return ["#" + t.lstrip("#").strip() for t in items if t and t.strip("#").strip()]


def pick(row, field, override):
    if override and override in row:
        return row[override]
    for key in DEFAULTS[field]:
        if key in row and row[key] not in (None, ""):
            return row[key]
    return None


def main():
    ap = argparse.ArgumentParser(description="采集数据 → 本仓标准格式")
    ap.add_argument("file", help="CSV 或 JSON（对象数组）")
    ap.add_argument("--platform", required=True, choices=["xiaohongshu", "douyin"])
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--query", nargs="*", default=[], help="本次采集用的搜索词，写进表头")
    ap.add_argument("--collected-at", default=dt.date.today().isoformat())
    for f in DEFAULTS:
        ap.add_argument(f"--{f.replace('_', '-')}-field", dest=f"{f}_field")
    args = ap.parse_args()

    if args.file.endswith(".csv"):
        with open(args.file, encoding="utf-8-sig") as fh:
            raw = list(csv.DictReader(fh))
    else:
        raw = json.load(open(args.file, encoding="utf-8"))
        if isinstance(raw, dict):
            raw = raw.get("rows") or raw.get("data") or sys.exit("JSON 里没找到数组")

    rows, no_likes = [], 0
    for r in raw:
        likes = to_int(pick(r, "likes", args.likes_field))
        no_likes += likes is None
        rows.append({"id": pick(r, "id", args.id_field),
                     "title": pick(r, "title", args.title_field),
                     "author": pick(r, "author", args.author_field),
                     "likes": likes,
                     "published_at": to_date(pick(r, "published_at", args.published_at_field)),
                     "url": pick(r, "url", args.url_field),
                     "tags": to_tags(pick(r, "tags", args.tags_field)),
                     "text": pick(r, "text", args.text_field)})

    out = {"platform": args.platform, "collected_at": args.collected_at,
           "query": args.query, "rows": rows}
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print(f"{args.out}：{len(rows)} 行，其中 {no_likes} 行无赞数（记 null，火力表会剔除并计数）")


if __name__ == "__main__":
    main()
