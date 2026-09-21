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
import pathlib
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
          "人味终检 8 类 AI 腔逐条改写（正文批注、照抄模板句已由机器判）",
          "来源可点：标签与句式确实指回火力表那几条（数字对不对已由 --fire-table 机器核）"]


NEGATION = re.compile(r"(不|别|勿|非|禁|忌|避免|删除|改写|替换|规避)[^。；\n]{0,6}$")
ORDINAL_OK = {"第一": "次天周步眼回遍期集章篇口批层缕根"}   # 「第一次」是序数，不是「第一名」


def exempt(text, w, i):
    """这一处命中是不是根本不算这个词：序数用法，或书名号里引的别人标题。"""
    nxt = text[i + len(w):i + len(w) + 1]
    if nxt and nxt in ORDINAL_OK.get(w, ""):
        return True
    line_end = text.find("\n", i)
    before = text[text.rfind("\n", 0, i) + 1:i]
    after = text[i:] if line_end < 0 else text[i:line_end]
    return before.rfind("《") > before.rfind("》") and "》" in after


def find(text, words):
    """返回 (真命中, 只在否定语境里出现的词)。

    合规警示段天然要写「不宣称生发」这类句子。只按关键词判死，
    等于逼着交付物不敢谈合规。所以命中处前 6 个字内若有否定词
    （不／禁／避免／替换……），记为提示而不是硬伤；
    只要有任意一处是裸用的，仍然判硬伤。
    """
    hard, negated_only = [], []
    for w in words:
        spots = [m.start() for m in re.finditer(re.escape(w), text) if not exempt(text, w, m.start())]
        if not spots:
            continue
        if all(NEGATION.search(text[max(0, i - 8):i]) for i in spots):
            negated_only.append(w)
        else:
            hard.append(w)
    return hard, negated_only


REJECT_MARK = re.compile(r"(驳回|未核实|无证据|未备案|待补|无报告|无检测|查无|存疑|宣传语|无背书|不作效果承诺)")
QUOTED = re.compile(r"[「『\"“]([^」』\"”\n]{2,20})[」』\"”]")
LIKES = re.compile(r"([0-9][0-9,\.]*)\s*(万)?\s*赞")
PLACEHOLDER = re.compile(r"〔[^〕\n]*占位[^〕\n]*〕")
TEACH_NOTE = "本例为教学示范"
DEMO_NUMBERS = ["2,029", "1,779", "1,512", "9,725", "181.8", "417+150", "398"]  # 模板与参考册里的示范数字


def rejected_claims(audit_text):
    """从审计段里捞出被判「驳回／未核实／待补」的说法。

    Claim Ledger 一行长这样：`| 5% 米诺地尔 | 客服口述 | 无备案 | 驳回 |`，
    也可能写成「『械字号』未核实」。两种都抽：先看整行有没有驳回标记，
    有就把行里被引号括起来的词、或表格首列，当成禁用说法。
    """
    out = []
    for line in audit_text.splitlines():
        if not REJECT_MARK.search(line):
            continue
        out += [q.strip() for q in QUOTED.findall(line)]
        if line.strip().startswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if cells and 2 <= len(cells[0]) <= 20 and not REJECT_MARK.search(cells[0]):
                out.append(cells[0])
    seen, uniq = set(), []
    for w in out:
        w = w.strip(" *`")
        if w and w not in seen and not w.startswith("---"):
            seen.add(w)
            uniq.append(w)
    return uniq


NUM_CLAIM = re.compile(r"[0-9]+(?:\.[0-9]+)?\s*(?:%|％|℃|度|倍|克|g|mg|小时|天)")


def claim_fragments(claim):
    """一条被驳回的说法拆成几块去查：整句、逗号切开的短句（≥4 字）、带单位的数字卖点。

    台账常写长句「39℃恒温发热科技，比普通棉暖3倍」，文案却改头换面成「39℃恒温科技」；
    只比整句会漏，所以数字卖点（39℃ / 3倍 / 5%）单独成块——这类数字换个说法照样是那条声明。
    """
    frags = [claim]
    frags += [p.strip() for p in re.split(r"[，,、；;。/]", claim) if len(p.strip()) >= 4]
    frags += [m.group(0).replace(" ", "") for m in NUM_CLAIM.finditer(claim)]
    seen, out = set(), []
    for f in frags:
        if f and f not in seen:
            seen.add(f)
            out.append(f)
    return out


def fragment_in(frag, text):
    """数字块要求前面不是数字（「95%」里不算有「5%」）。"""
    if NUM_CLAIM.fullmatch(frag):
        return re.search(r"(?<![0-9.])" + re.escape(frag), text.replace(" ", "")) is not None
    return frag in text


def likes_numbers(text):
    """抽出文本里所有「N 赞」的数字原样（含万）。"""
    return [(m.group(1) + ("万" if m.group(2) else "")) for m in LIKES.finditer(text)]


def table_numbers(text):
    """火力表里出现过的所有数字原样（含万）。表里「加权赞 5,626」把赞写在前面，
    只认「N 赞」会把真数字误判成瞎编，所以这一侧放宽到全部数字。"""
    return {m.group(1) + ("万" if m.group(2) else "")
            for m in re.finditer(r"([0-9][0-9,\.]*)\s*(万)?", text) if m.group(1)}


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


def sections(text):
    """逐行给出 (行号, 所在小节标题, 行)。行号从 1 起，和编辑器一致。"""
    head = ""
    for n, line in enumerate(text.splitlines(), 1):
        m = re.match(r"^#{1,6}\s*(.+)$", line.strip())
        if m:
            head = m.group(1)
        yield n, head, line


def title_lines(text):
    """「标题：xxx」一行，或「标题主推」小节下用「」括起来的那一条。

    模型写的交付物大多是后一种，只认前一种等于标题检查形同虚设。
    备选留档不发出去，不查。
    """
    out = []
    for _, head, line in sections(text):
        s = line.strip().lstrip("#").strip()
        if re.match(r"^(标题|主推标题)[:：]", s):
            out.append(s.split("：", 1)[-1].split(":", 1)[-1].strip())
        elif "标题" in head and "备选" not in head and not s.startswith(("—", "(", "（", "#")):
            m = re.match(r"^(?:[0-9]+[.、]\s*)?\**「([^」\n]{4,})」", s)
            if m:
                rest = s[m.end():].strip("* ")
                # 「前半」｜后半 这种写法，后半也是标题的一部分，锚点和违禁都要一起查
                out.append(m.group(1) + (rest if rest.startswith(("｜", "|")) else ""))
    return out


def where(text, word):
    """硬伤指路：这个词在文案段第一次裸出现的行号和那一行，给修复轮照着改。"""
    for n, head, line in sections(text):
        if any(k in head for k in AUDIT_HEADINGS):
            continue
        i = line.find(word)
        if i >= 0 and not exempt(line, word, i):
            return f"第 {n} 行「{line.strip()[:40]}」"
    return ""


PASTE_SECTIONS = ["正文", "口播"]
ANNOTATION = re.compile(r"[（(](?:[AIDA][，,]|[^）)\n]*(?:句式|赞|痛点|人格背书|钩子|暗踩|规避|连载仪式|"
                        r"实证|说真话体|反转起手|证据|火力|公式))[^）)\n]*[）)]")


def annotated_lines(text):
    """正文／口播里用户会直接复制发出的句子（> 开头），夹着写法批注的行。

    批注是写给自己看的，发出去就是「这号在按公式写」的铁证，也是真人味
    扣分的头号原因（9-19 盲评三道题正文句句带括号）。拆解一律挪进证据行。
    """
    out = []
    for n, head, line in sections(text):
        if line.strip().startswith(">") and any(k in head for k in PASTE_SECTIONS) \
                and ANNOTATION.search(line):
            out.append(n)
    return out


TEMPLATE = pathlib.Path(__file__).resolve().parents[1] / "templates" / "copy-package.md"


def template_sentences():
    """模板示范成稿里的每一句（≥8 字）。示范句是教格式的，照抄进交付物就是别人的话。"""
    if not TEMPLATE.exists():
        return []
    out = []
    for line in TEMPLATE.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if s.startswith(">") or s.startswith("「"):
            s = re.sub(r"[（(][^）)\n]*[）)]", "", s.split("——")[0])
            out += [p for p in re.split(r"[，。？！、：；「」>｜\s]+", s) if len(p) >= 8]
    return out


def main():
    ap = argparse.ArgumentParser(description="文案包出厂扫描（SKILL.md ⑥）")
    ap.add_argument("file")
    ap.add_argument("--single-platform", choices=["xiaohongshu", "douyin"],
                    help="只有单平台证据时，检查跨平台措辞")
    ap.add_argument("--observational", action="store_true",
                    help="火力表为观察级时，检查「实测最火」类表述")
    ap.add_argument("--fire-table", metavar="文件", nargs="+",
                    help="本轮材料：火力表（④段产出），可再跟本轮样本表。"
                         "给了就核对证据行里的赞数是不是本轮的数字，不是模板或瞎编的")
    args = ap.parse_args()

    text = open(args.file, encoding="utf-8").read()
    copy_text, audit_text = split_audit(text)
    hard, soft = [], []

    for label, words in [("万能补丁黑名单（闸一）", BLACKLIST), ("极限词（合规 §1）", EXTREME),
                         ("医疗越线（合规 §2）", MEDICAL), ("站外导流（合规 §3）", DRAIN)]:
        hit, negated = find(copy_text, words)
        if hit:
            hard.append(f"{label}：" + "、".join(f"{w}（{where(text, w)}）" if where(text, w) else w
                                              for w in hit))
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

    # ⑤闸〇 声明落地：台账里判了驳回／未核实的说法，不许出现在会发出去的文案里
    for claim in rejected_claims(audit_text):
        hit = next((f for f in claim_fragments(claim) if fragment_in(f, copy_text)), None)
        if hit:
            hard.append(f"无证据声明进了文案（⑤闸〇）：台账判「{claim}」不可用，文案里仍在说「{hit}」"
                        f"（{where(text, hit)}）——整句换掉，标题刺点也要换，不许只在闸门记录里写「未使用」")

    # ⑥ 人味终检：会被直接复制发出的句子不许夹批注，不许照抄模板示范句
    notes = annotated_lines(text)
    if notes:
        hard.append("正文／口播里夹着写法批注（⑥人味终检）：第 " + "、".join(map(str, notes[:8]))
                    + " 行；括号里的公式名和赞数挪进证据行，成稿要能原样复制发出")
    copied = sorted({t for t in template_sentences() if t in copy_text})
    if copied:
        hard.append("照抄了模板的示范句（⑥人味终检）：" + "、".join(f"「{t}」" for t in copied[:4])
                    + "；示范句只教格式，换成本产品、本人设自己的话")

    # ⑥ 来源可点：证据行的赞数必须来自本轮火力表
    if PLACEHOLDER.search(text):
        hard.append("模板占位符原样抄进了交付物（⑥来源可点）："
                    + "、".join(sorted(set(PLACEHOLDER.findall(text)))[:3])
                    + "；占位符不是数据，必须换成本轮火力表算出来的数字")
    if TEACH_NOTE in text:
        hard.append("把模板的教学注解也抄进了交付物（⑥来源可点）：「" + TEACH_NOTE + "」")

    used = likes_numbers(text)
    demo = sorted({n for n in used for d in DEMO_NUMBERS if n.startswith(d) or d.startswith(n)})
    if demo:
        hard.append("证据行抄了模板／参考册的示范赞数（⑥来源可点）：" + "、".join(demo))
    if args.fire_table:
        table = "\n".join(open(f, encoding="utf-8").read() for f in args.fire_table)
        table_nums = {n.replace(",", "") for n in table_numbers(table)}
        orphan = sorted({n for n in used if n.replace(",", "") not in table_nums} - set(demo))
        if orphan:
            hard.append("证据行的赞数指不回本轮材料（⑥来源可点）：" + "、".join(orphan))
    elif used:
        soft.append("没给 --fire-table，证据行的 " + str(len(used)) + " 个赞数只能人工核对是否来自本轮")

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
