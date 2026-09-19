# 采集数据格式（喂给 scripts/fire_table.py 的那一份）

本仓不带采集器。采集工具各人本机不同（浏览器登录态 CLI、MediaCrawler、All-IN-ONE、
自己手抄都行），所以约好一个中间格式：**你的采集器负责把数据变成下面这个 JSON，
后面的火力表计算和闸门判定由脚本接手。**

## 格式

```json
{
  "platform": "xiaohongshu",
  "collected_at": "2026-09-19",
  "query": ["防脱洗发水", "达霏欣"],
  "rows": [
    {
      "id": "6aaa51cf00000000260163cb",
      "title": "精细化分类❗️我看看谁还不会挑洗发水！！",
      "author": "朱旺旺就是朱旺旺呗",
      "likes": 2275,
      "published_at": "2026-09-16",
      "url": "https://www.xiaohongshu.com/search_result/6aaa51cf...",
      "tags": ["#洗发水", "#细软塌", "#油头"],
      "text": "正文或视频文案（可选，没有 tags 时脚本会从这里抽 #标签）"
    }
  ]
}
```

| 字段 | 必填 | 说明 |
|---|---|---|
| platform | 是 | `xiaohongshu` 或 `douyin`，两边闸门阈值不同 |
| rows[].likes | 是 | 整数；**采不到写 `null`，不要写 0**，脚本会把 null 行剔除并计数 |
| rows[].published_at | 建议 | `YYYY-MM-DD`；没有就按「日期未知」计入，并在表脚标注（90 天衰减闸会失效，交付要说明） |
| rows[].tags | 建议 | 数组；没有就留空，脚本从 `text`/`title` 里抽 `#标签` |
| rows[].url | 建议 | 「来源可点」闸要用：每个主标签都要指得回带赞的原始链接 |
| id / author / title / text | 否 | 有就填，出表时用来写证据行 |

## 怎么生成

- **手动**：Excel 填上面的列，导出 CSV，跑 `python3 scripts/normalize.py 采集.csv --platform xiaohongshu -o xhs.json`。
- **命令行采集器**：把它的 JSON 输出字段映射成上表。本仓 `examples/` 里的两份数据就是
  这么来的（浏览器登录态 CLI 搜索 + 逐条详情补标签），命令和口径写在
  `examples/README.md`。
- **没有采集器**：只跑单平台，甚至手抄 20-30 条也能跑——闸门会自己把样本不足的结论降级，
  这正是它存在的理由。

## 然后

```bash
python3 scripts/fire_table.py xhs.json douyin.json --asof 2026-09-19
```

输出是一张带闸门判定的火力表（主表 + 弱证据附录），直接贴进第④段产出。
