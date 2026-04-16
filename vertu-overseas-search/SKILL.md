---
name: vertu-overseas-search
description: "Search overseas restaurants, venues, and local services for VERTU concierge staff handling international customer requests. Use when a customer asks to find restaurants, make dining reservations, or discover venues in cities outside mainland China. Triggers on: 帮我找餐厅, 预订餐厅, 推荐餐厅, 订位, restaurant/venue search for any international city, or when a customer provides a city and dining/activity request."
---

# VERTU 海外餐厅 & 场馆搜索

## 核心场景

管家接收到海外客户咨询，需要快速找到：
- 当地优质餐厅（含米其林、高端、普通多档）
- 特殊场合推荐（商务宴请、浪漫约会、家庭聚餐）
- 是否需要提前预订，以及预订方式

---

## 信息收集（先问再查）

开始搜索前，确认以下必要信息。如果客户已提供，直接进入搜索步骤。

**必须确认：**
- 城市（精确到城市，不只是国家）
- 用餐人数
- 用餐时间（今晚 / 明天 / 具体日期）

**有助于精准推荐：**
- 场合（商务 / 约会 / 朋友聚餐 / 家庭 / 庆祝）
- 菜系偏好（本地菜 / 日料 / 法餐 / 无要求）
- 预算级别（便餐 / 中高档 / 米其林级别）
- 特殊要求（包间 / 海景 / 靠近某酒店 / 素食）

---

## 搜索策略

每次搜索组合使用 2-3 个关键词模式，以提高结果质量：

### 搜索词模板

```
[城市] best [菜系/occasion] restaurant [year]
[城市] Michelin restaurant guide
[城市] fine dining reservation required
[城市] top rated restaurant tripadvisor
[城市] [菜系] restaurant not tourist trap
```

**禁止只搜通用词**（结果多为广告）：
- ❌ `paris restaurant`
- ✅ `paris best french bistro locals recommend 2025`

### 搜索来源优先级

见 [references/search-sources.md](references/search-sources.md)

---

## 输出格式

每次给出 **3-5 家**推荐，格式统一：

```
餐厅名（本地文字 / 英文）
类型：米其林★★ / 高端 / 休闲
菜系：法式 / 日料 / 本地菜…
人均：€80-120 / $50-80（按当地货币）
必须预订：是（建议提前X天） / 建议预订 / 不需要
特色：一句话亮点
预订方式：官网链接 / TheFork / OpenTable / 电话
地址：（简短）
```

输出后附加：
- **数据说明**：本次搜索时间，建议管家在推荐前致电或查官网二次确认营业状态
- **替补选项**：列 1-2 家如果首选无法预订的备选

---

## 注意事项

- 信息时效性：餐厅信息动态变化，推荐前应二次确认营业状态
- 广告识别：搜索结果前排多为推广，优先采用 TripAdvisor 评分、米其林指南、本地美食博主内容
- 预订渠道：帮客户找到正确渠道比只给电话更可靠（详见 references/search-sources.md）
