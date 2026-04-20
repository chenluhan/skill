# verified-travel-planner 设计说明

## 结论

建议创建一个名为 `verified-travel-planner` 的 skill，默认安装在 `~/.codex/skills/verified-travel-planner/`。

它的定位不是“写一份旅游攻略”，而是：

- 把模糊的出行需求补全成结构化输入
- 用真实来源拉取或核验预算关键项
- 把已核验与未核验项明确分开
- 输出一份带证据链的可视化 PDF

第一版只做 `中国大陆境内游`，最多支持 `3 个停留点`，且只承诺 `大交通 + 酒店 + 门票` 的准确预算。

## 核心原则

这个 skill 的第一原则不是内容丰富，而是预算可信。

因此它必须遵守这些硬规则：

- 在必填需求缺失前，不允许查询价格
- 没有来源、时间戳和条件的价格，不允许进入总预算
- 火车票不允许按固定价假设，必须以 `12306` 官方查询链路为准
- 任何外部依赖失败时，必须显式降级，不能伪造精确结果

## 用户问题

用户真正要解决的问题，不是“帮我安排行程”，而是：

- 给我一条可执行的国内旅游路线
- 告诉我这条路线大概要花多少钱
- 告诉我这个预算是根据什么真实来源算出来的
- 如果缺数据，明确指出哪里没法算准

普通旅游攻略类输出的问题在于：

- 价格常常来自旧网页、营销页或模型臆测
- 预算表看起来完整，但无法追溯
- 路线安排与真实交通耗时脱节
- 一旦价格链断了，仍然假装“已经规划完成”

这个 skill 要反过来设计：宁可少给，也不能假给。

## 范围与非目标

### 范围

第一版负责：

- 需求补全与结构化归一
- 机票 / 酒店 / 景点票的实时报价接入
- `12306` 官方链路的火车票核验
- `高德` 的地理编码、POI 与路线时间核验
- 预算闭合检查
- 行程清单、预算表与证据链 PDF 输出

### 非目标

第一版不负责：

- 代订机票、酒店或门票
- 国际游
- 超过 3 个停留点的复杂联游
- 餐饮、购物、市内打车的精确预算
- 自驾油费、电费和高速费的准确预算
- 无来源情况下的“估算补齐”

## 数据源策略

推荐采用 `单主供应商 + 核验兜底`。

### 主路径

- 机票 / 酒店 / 景点票：`飞猪 AI 开放平台 / OpenClaw`
- 路线与 POI：`高德开放平台`
- 火车票：`12306` 官方公网查询链路

### 可选后备

- 酒店：`艺龙开放平台`

第一版不把艺龙做成主路径，原因很简单：如果一开始就把多供应商拼装成默认路径，skill 会更脆、更难解释失败原因，也更难保证预算口径一致。

## 自驾能力

第一版需要支持 `自驾`，但要把“支持路线”与“支持准确成本”拆开。

### 第一版支持

- `transport_preferences` 接受 `self_drive`
- 用高德生成连续停留点之间的自驾路线
- 输出每段的里程、时长和过路费
- 如果用户提供 `vehicle_profile`，基于能耗与每单位能源价格给出自驾成本估算

### 第一版不承诺

- 把自驾成本并入准确总价
- 在没有车辆参数时推测油费或电费
- 在没有可靠来源时给出“差不多”的高速费

这意味着自驾在第一版里是 `路线核验 + 条件化估算`，不是 `准确报价`。

## 核心数据契约

### trip-request.json

输入标准件，至少包含：

- `origin`
- `stops[]`
- `date_range`
- `travelers`
- `rooms`
- `budget_mode`
- `budget_target`
- `hotel_level`
- `transport_preferences`
- `must_see`
- `constraints`

### quote-records.json

报价记录件。每条报价至少包含：

- `category`
- `provider`
- `product_name`
- `source_ref`
- `queried_at`
- `unit_price`
- `total_price`
- `currency`
- `conditions`
- `verification_status`
- `traveler_scope`

同时允许附带 `segment_key`、`booking_url`、`metadata` 等扩展字段。

### itinerary-manifest.json

最终交付件，至少包含：

- `summary`
- `stop_order`
- `day_plans[]`
- `verified_budget`
- `unverified_items[]`
- `booking_links[]`
- `evidence_refs[]`

## Skill 工作流

### 1. 需求补全

必须确认：

- 出发地
- 停留点列表
- 出发/返程日期
- 出行人数与乘客结构
- 房间需求
- 预算模式
- 交通偏好

默认值：

- 酒店档位：`midscale`
- 每日节奏：`morning_anchor + afternoon_anchor + free_evening`
- 餐饮 / 购物 / 临时打车：不进精确预算

### 2. 结构化归一

把会话归一成 `trip-request.json`，并在这一步就拒绝不完整输入。

### 3. 实时报价与核验

策略分三层：

- 主供应商报价
- 官方链路核验
- 路线与 POI 辅助证据

只要任一预算关键项未被核验，该项就必须被剔出总预算，并在最终结果里保留未闭合提示。

### 4. 行程合成与 PDF 输出

输出至少包括：

- 1 个主方案
- 预算超额时的 1 个更省钱备选
- 每日路线安排
- 已核验预算卡片
- 未闭合项清单
- 来源与查询时间

## 实现结构

skill 目录保持精简：

```text
verified-travel-planner/
├── SKILL.md
├── agents/
│   └── openai.yaml
├── references/
│   ├── data-contracts.md
│   └── provider-contracts.md
├── scripts/
│   ├── _travel_common.py
│   ├── check_dependencies.py
│   ├── normalize_trip_request.py
│   ├── collect_live_quotes.py
│   ├── build_itinerary.py
│   └── render_trip_pdf.py
└── assets/
    └── report.css
```

运行产物统一写入：

```text
notes/travel-planner-runs/YYYY-MM-DD-<trip-slug>/
```

## 外部运行时设计

飞猪主路径不直接绑定某个尚不稳定的本地 CLI 名称，而是抽象成两个桥接模式：

- `FLYAI_OPENCLAW_CMD`
- `FLYAI_OPENCLAW_ENDPOINT`

这样 skill 可以在不同环境下接：

- 本地命令包装器
- 本地代理服务
- 团队内部统一网关

只要桥接器满足 skill 约定的 JSON 输入输出契约，主流程不需要改。

## 失败策略

失败不是异常路径，而是设计的一部分。

必须明确处理：

- `高德 key` 缺失
- `OpenClaw` 未配置
- `12306` 查询链路返回 HTML 错页或被限制
- `pandoc / weasyprint` 缺失
- 某一项报价存在，但缺条件或缺来源

统一原则：

- 输出可读的失败原因
- 写出中间文件
- 不伪造“准确总价”

## 验证策略

至少验证这 5 个脚本的代表性路径：

- `check_dependencies.py` 能输出机器可读依赖报告
- `normalize_trip_request.py` 能拒绝缺必填项的输入并填补默认值
- `collect_live_quotes.py` 在缺 provider 时能写出失败原因，在有 `12306` 官方可达链路时能尝试真实查询
- `build_itinerary.py` 能基于部分核验结果生成未闭合预算提示
- `render_trip_pdf.py` 能在本机 `pandoc + weasyprint` 环境下导出 PDF

## 取舍说明

### 为什么不是网页搜索优先

网页搜索适合找补充信息，不适合做预算主链路。旅游价格最怕“看起来像真的”，所以主路径必须走明确供应商或官方查询链路。

### 为什么火车票保留在 v1

国内游不做火车票，会直接削弱 skill 的实用性。  
但火车票也不能强依赖一个开发者平台，所以第一版走 `12306` 官方公网查询链路，能查就核验，查不到就降级。

### 为什么不算餐饮和打车

这些成本波动大，且大多数场景下很难通过稳定官方源闭合。第一版把精力集中在对用户影响最大的硬预算项，路线更稳，解释也更清楚。
