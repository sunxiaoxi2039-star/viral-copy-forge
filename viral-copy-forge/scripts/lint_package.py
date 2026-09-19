#!/usr/bin/env python3
"""文案包出厂扫描（SKILL.md ⑥段里能机器判的那部分）。

用法：
    python3 scripts/lint_package.py 交付.md
    python3 scripts/lint_package.py 交付.md --single-platform xiaohongshu

只查「机器能判死」的项：黑名单词、极限词、医疗越线、导流、跨平台越界、
交付五件套是否齐、主推是否只有 1 条、标题有没有锚点。
判不了的（人味、换品名死亡测试、记忆点复刻）由人或模型按 SKILL.md ⑥ 过，
本脚本会把它们列成待人工项，不假装通过。
退出码：0 = 无硬伤，1 = 有硬伤。
"""

import argparse
import re
import sys

BLACKLIST = ["有图有真相", "亲测有效", "闭眼入", "打工人必备"]          # 万能补丁（闸一）
EXTREME = ["最好", "第一", "顶级", "极致", "绝对", "100%", "国家级", "全网最",
           "史上", "独家", "首个", "彻底", "根治", "永久", "无效退款"]      # compliance §1
MEDICAL = ["生发", "育发", "治疗脱发", "治愈", "药效", "替代药物", "根治脱发"]  # compliance §2
DRAIN = ["私信我领", "加微信", "vx", "威信", "V信", "公众号领"]            # compliance §3
CROSS_PLATFORM = ["全网", "全平台", "两个平台", "双平台都火", "各大平台"]     # ⑤段数据完整性
AI_TONE = ["首先", "其次", "综上所述", "值得注意的是", "赋能", "打造", "助力",
           "惊艳", "专家表示", "研究表明"]                                 # compliance §5，提示不判死
UNVERIFIED = ["实测最火", "最火的标签", "平台最火", "公认最火"]              # ④段观察级禁语
REQUIRED = {
    "文案本体": ["标题", "正文"],
    "证据行": ["证据"],
    "合规警示": ["合规"],
    "数据缺口声明": ["数据缺口", "缺口声明"],
    "丑话三句": ["丑话"],
}
ANCHOR = re.compile(r"[0-9０-９]|第[一二三四五六七八九十]|天|元|块|岁|年|周|个月")
MANUAL = ["闸二 换品名死亡测试：品名换成竞品名后句子是否塌",
          "闸三 自评门四项打分，交付最高版",
          "闸四 洗稿判定：与竞品原文相似度",
          "人味终检 8 类 AI 腔逐条改写",
          "来源可点：每个主标签指回火力表带赞来源"]


NEGATION = re.compile(r"(不|别|勿|非|禁|忌|避免|删除|改写|替换|规避)[^。；\n]{0,6}$")


def find(text, words):
    """返回 (真命中, 只在否定语境里出现的词)。

    合规警示段天然要写「不宣称生发」这类句子。只按关键词判死，
    等于逼着交付物不敢谈合规。所以命中处前 6 个字内若有否定词
    （不／禁／避免／替换……），记为提示而不是硬伤；
    只要有任意一处是裸用的，仍然判硬伤。
    """
    hard, negated_only = [], []
    for w in words:
        spots = [m.start() for m in re.finditer(re.escape(w), text)]
        if not spots:
            continue
        if all(NEGATION.search(text[max(0, i - 8):i]) for i in spots):
            negated_only.append(w)
        else:
            hard.append(w)
    return hard, negated_only


AUDIT_HEADINGS = ["产品卡", "证据行", "合规", "Claim Ledger", "闸门", "数据缺口", "丑话"]


def split_audit(text):
    """把「会发出去的文案」和「只给自己看的审计段」分开。

    证据行、合规警示、闸门记录里天然要写「单条贡献 100%」「不宣称生发」
    这类词——它们是审计语言，不是投放语言。审计段里的命中记为提示，
    文案段里的命中才判死。没有任何标题时，整篇按文案段处理（从严）。
    """
    copy_parts, audit_parts = [], []
    bucket = copy_parts
    for line in text.splitlines():
        m = re.match(r"^#{1,6}\s*(.+)$", line.strip())
        if m:
            head = m.group(1)
            bucket = audit_parts if any(k in head for k in AUDIT_HEADINGS) else copy_parts
        bucket.append(line)
    return "\n".join(copy_parts), "\n".join(audit_parts)


def title_lines(text):
    out = []
    for line in text.splitlines():
        s = line.strip().lstrip("#").strip()
        if re.match(r"^(标题|主推标题)[:：]", s):
            out.append(s.split("：", 1)[-1].split(":", 1)[-1].strip())
    return out


def main():
    ap = argparse.ArgumentParser(description="文案包出厂扫描（SKILL.md ⑥）")
    ap.add_argument("file")
    ap.add_argument("--single-platform", choices=["xiaohongshu", "douyin"],
                    help="只有单平台证据时，检查跨平台措辞")
    ap.add_argument("--observational", action="store_true",
                    help="火力表为观察级时，检查「实测最火」类表述")
    args = ap.parse_args()

    text = open(args.file, encoding="utf-8").read()
    copy_text, audit_text = split_audit(text)
    hard, soft = [], []

    for label, words in [("万能补丁黑名单（闸一）", BLACKLIST), ("极限词（合规 §1）", EXTREME),
                         ("医疗越线（合规 §2）", MEDICAL), ("站外导流（合规 §3）", DRAIN)]:
        hit, negated = find(copy_text, words)
        if hit:
            hard.append(f"{label}：{'、'.join(hit)}")
        if negated:
            soft.append(f"{label}只出现在否定句里（如「不宣称…」），已放行，人工确认：{'、'.join(negated)}")
        a_hit, _ = find(audit_text, words)
        if a_hit:
            soft.append(f"{label}出现在审计段（证据行／合规／闸门记录），不算投放语言，人工确认："
                        f"{'、'.join(a_hit)}")

    if args.single_platform:
        hit, _ = find(copy_text, CROSS_PLATFORM)
        if hit:
            hard.append(f"单平台证据却用了跨平台措辞（⑤段）：{'、'.join(hit)}")
    if args.observational:
        hit, _ = find(copy_text, UNVERIFIED)
        if hit:
            hard.append(f"观察级火力表却宣称实证（④段）：{'、'.join(hit)}")

    missing = [name for name, keys in REQUIRED.items() if not any(k in text for k in keys)]
    if missing:
        hard.append("交付五件套缺：" + "、".join(missing))

    main_push = len(re.findall(r"主推", text))
    if main_push == 0:
        hard.append("没有标出主推条（⑤交付规则：主推只交 1 条）")

    titles = title_lines(copy_text)
    for t in titles:
        if not ANCHOR.search(t):
            hard.append(f"标题缺锚点（数字/天数/价格/身份）：{t[:30]}")

    hit, _ = find(copy_text, AI_TONE)
    if hit:
        soft.append("疑似 AI 腔／膨胀词，人工复核：" + "、".join(hit))
    if not titles:
        soft.append("没识别出「标题：」行，标题类检查已跳过")

    print(f"# 出厂扫描 · {args.file}")
    print(f"\n硬伤 {len(hard)} 条")
    for h in hard:
        print(f"- ❌ {h}")
    if not hard:
        print("- 无")
    print(f"\n提示 {len(soft)} 条")
    for s in soft:
        print(f"- ⚠️ {s}")
    if not soft:
        print("- 无")
    print("\n机器判不了、必须人工或模型过的：")
    for m in MANUAL:
        print(f"- ☐ {m}")
    return 1 if hard else 0


if __name__ == "__main__":
    sys.exit(main())
