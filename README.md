# viral-copy-forge · 爆款文案锻造坊

> 你管这叫商业机密？不过是把小红书 9725 赞的医生钩子、抖音 189 万赞的反转句式，摆到你的产品名字前面——**四步搬数、四步排序**，谁都能装，我们只是把它写成了流水线。真正难的从来不是这张图，是你敢不敢承认，自己上一条没火的笔记，一直缺的是一张标签火力表。
>
> **viral-copy-forge** 就是这条流水线：给产品名和竞品名，产出每个钩子都指得回真实带赞笔记的文案包。不保证爆，只保证不瞎编。

## 30 秒说清楚

**这是干什么的**：你给一个产品名 + 竞品名，它去小红书和抖音把这个品类今天真的在火的标题、标签、句式扒下来，按累计点赞排序，再拆竞品的记忆点（成分昵称、使用仪式、人群细分），最后把两样东西揉进一条新文案里——每条标题必须挂上所用标签和来源笔记的赞数，来源链接要能点开。
火力表由 `scripts/fire_table.py` 算，交付前由 `scripts/lint_package.py` 扫，两者的阈值由 `tests/` 锁死，不靠自觉。

**跟同类有什么不一样**：同类项目不少，做得也比我们全——[social-account-doctor](https://github.com/JuneYaooo/social-account-doctor)（小红书+抖音等五个平台，采集和爆款拆解都有）、[lingzao-skill](https://github.com/atian-create/lingzao-skill)（小红书+抖音+公众号，有对标账号和爆款拆解）、[viral-note-agent-skill](https://github.com/xuboboo/xiaohongshu-viral-note-agent-skill)（选题、生成、合规门禁、发布、复盘闭环）、[All-IN-ONE](https://github.com/cv-cat/All-IN-ONE)（多平台采集）、[都爆鸭](https://github.com/zizhanovo/doubaoya-community)（多平台爆文聚合）。我们只做窄的一件事：**按累计点赞给标签排火力，样本不够就自动降级、一条爆款不许带飞整张表**。在我们 2026-09-19 查过的公开项目里，没看到把这套样本闸门写明的。完整对照见 [docs/RESULTS.md](docs/RESULTS.md#竞品对照)。

**效果数据**：2026-09-19 用真实采集数据完整跑了一次，产物全在 [examples/](examples)（含一次「抖音主表为空」的降级结论）。另有早期打分：同一产品、同一把评分尺（6 维）下，v1 对「不用 skill 的认真写法」自测均分 50:38；一次 AI 单评委（Kimi）、单案例的匿名盲评里，v1 得 52/60，高于早期流水线（35）和无 skill 基线（23）。样本很小，详见 [docs/RESULTS.md](docs/RESULTS.md)。

**怎么装**：见下面「安装」，3 步。

---

## 5 分钟跑一遍（不用装 skill，也不用模型密钥）

仓里带了 2026-09-19 真实采集的一份数据和它跑出来的全部产物，`git clone` 后直接复现：

```bash
# 1. 从采集数据算火力表（小红书 50 条 + 抖音 20 条）
python3 viral-copy-forge/scripts/fire_table.py \
    examples/data/xhs-2026-09-19.json examples/data/douyin-2026-09-19.json \
    --asof 2026-09-19

# 2. 把产出的文案包过一遍出厂扫描（⑥段里机器能判死的部分）
python3 viral-copy-forge/scripts/lint_package.py \
    examples/out/copy-package-2026-09-19.md --observational

# 3. 看用例清单，并让机器判一遍你自己的成品
python3 viral-copy-forge/evals/run_evals.py --case case1-mandi-anti-hairloss \
    --package examples/out/copy-package-2026-09-19.md --observational

# 4. 闸门一致性 + 出厂扫描的测试（纯标准库，无依赖）
python3 tests/test_gates.py && python3 tests/test_lint.py
```

你自己的数据怎么喂进来：CSV 或 JSON 先过 `scripts/normalize.py`，格式契约见 [docs/DATA_SCHEMA.md](docs/DATA_SCHEMA.md)。
手抄 20-30 条也能跑——样本不够时闸门会自动降级，不会假装实证。

## 真实产物（2026-09-19，数据和结论都在仓里）

| 产物 | 文件 |
|---|---|
| 采集数据（小红书 50 / 抖音 20） | [examples/data/](examples/data) |
| 火力表 | [examples/out/fire-table-2026-09-19.md](examples/out/fire-table-2026-09-19.md) |
| 文案包（⑤⑥段成品） | [examples/out/copy-package-2026-09-19.md](examples/out/copy-package-2026-09-19.md) |

这一轮最能说明这个 skill 是干什么的，是它交出来的两个「不好看」的结论：

- **抖音整表判了观察级、主表为空**。20 条视频一条都没拿到发布日期，时间衰减闸失效，先降级；再往下没有一个话题过最小样本闸，连 179.7 万赞那条所在的 #达霏欣防脱洗发水 也只挂了 4 条视频，被判进弱证据附录。没有实证就写没有，不凑一个第一名交差。
- **「5% 米诺地尔」「械字号」被 Claim Ledger 拦在文案外**。前者是药品成分，洗发水按化妆品管理不得这样宣称；后者没有备案号截图。两条都记在台账里，一个字没进正文。

小红书那半边是实测级（50 条、中位赞 148、爆款线 444），主表 4 个标签，每条证据都能点开：
[#防脱洗发水 8 条爆款／加权赞 7,641／样本 15 条](examples/out/fire-table-2026-09-19.md)，
来源如 [发量多到"嚣张"是什么体验？ 2,231 赞](https://www.xiaohongshu.com/explore/6a64b378000000000103075e)。

> 赞数来自公开笔记的抓取日快照，仅作结构证据，不代表原作者与本项目有合作，也不代表生成文案的预计表现。

## 六段流水线

```
①输入与校准 → ②双平台采集 → ③竞品属性解剖 → ④标签火力实证 → ⑤组合生成 → ⑥质检与交付
```

第 ④ 段是核心差异化：不靠感觉判断「什么标签会火」，靠**同类目/竞品笔记的累计点赞排序**——小红书看笔记赞，抖音看话题下所有视频的累计赞。方法不神秘，四步：**搬数据、提标签、拆竞品、重组生成**——流程图上没有一步是魔法，谁都能装。

内置六道质量闸（这是它和「模板生成器」的区别）：

| 闸 | 拦什么 |
|---|---|
| 换品名死亡测试 | 换个牌子句子还成立 = 品类通用句，作废重写 |
| 刺点配额 | 每条标题必须含 1 个产品卡里的不可公式化元件，禁用「有图有真相」类万能补丁 |
| 样本闸 | 单平台样本不足、或过半样本连发布日期都没有时，火力表降级为「观察级」，不宣称实证 |
| 离群封顶 | 一条百万赞爆款不许带飞整张火力表 |
| 记忆点不可互换 | 竞品记忆点贴到你的产品上要「别扭」才算数 |
| 出厂三问 | 换品名复测 + 来源可点 + 平庸检测，全过才交付 |

## 安装

1. 把 `viral-copy-forge/` 整个文件夹放进 `~/.claude/skills/`（或你项目的 `.claude/skills/`）。
2. 确认 `SKILL.md` 在该文件夹根目录——加载器靠它的 `description` 决定什么时候自动装载，不用手动 `/load`。
3. 在会读 `SKILL.md` 的环境（Claude Code 及兼容加载器）里，说一句「帮我写个爆款文案」或「给 XX 产品 tag 一下小红书热标签」，它会自己触发。

`scripts/`、`tests/`、`evals/` 只要 Python 3.8+，无第三方依赖，不装 skill 也能单独用。

> **采集工具要自备**：本仓只有流程和规则，不带任何采集脚本。小红书和抖音的数据都要靠你自己的采集工具（比如 [All-IN-ONE](https://github.com/cv-cat/All-IN-ONE) 或已登录的浏览器会话）喂进来，否则第②段会卡住。抖音没有官方 API，首次用请看 `references/douyin.md` 里的边界说明。

## What this is NOT

- **不是自动发布机器人**——生成完文案不会帮你发出去，自动发布接线只有可选说明，默认关。
- **不是投放/出价优化工具**——点赞是「这个标签曾经有人看」的代理指标，不等于你投出去的 CTR/CVR，钱要自己去投放台测。
- **不是纯润色或纯翻译工具**——没有竞品数据和标签火力表介入的场景（比如你只是要把英文文案翻成中文），这个 skill 不该触发，用别的润色类 skill。
- **不是学术写作或严肃文档助手**——它天生带营销腔和情绪钩子，写论文别找它。
- **不保证防编造**——Claim Ledger（证据台账）只在功效、母婴、食品类强制开，其他品类默认关；开着也只是提醒你核对，别拿它当免责声明生成器。

## 三句丑话

1. 标签组合不保证巨大流量——它只是把「被验证过有人看的词」装进你的笔记，起跑线从 0 分提到 60 分，剩下 40 分靠内容和投流的钱。
2. 平台会查重，句式可以借，内容必须换皮。
3. 抖音这半边通道不如小红书稳，装之前先看清楚边界说明。

---

## License

MIT

## Author

viral-copy-forge contributors

## Acknowledgements

技能文件格式参考了 [anthropics/skills](https://github.com/anthropics/skills) 的公开规范。六维热度权重和 12 类标题机制改编自 [viral-note-agent-skill](https://github.com/xuboboo/xiaohongshu-viral-note-agent-skill)（MIT），原版权声明见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。竞品对照基于各项目公开文档；viral-note-agent-skill 另做过一次本机实跑。
