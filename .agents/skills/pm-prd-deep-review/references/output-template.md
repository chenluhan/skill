# Output Template

Use this template for the final Markdown report.
Adapt the depth to the PRD quality, but keep the section order.
Quote or paraphrase original PRD text for major findings whenever possible.

## Report Skeleton

```md
# 审查结论
- 结论：适合进入评审 / 需要补完后再评审 / 暂不适合进入开发
- 风险等级：高 / 中 / 低
- 一句话判断：用一句话说明最核心的问题
- 审查范围：说明本次依据的文档和可见信息

# 关键致命问题
| 严重级别 | 问题 | 关联原文或章节 | 对用户/业务的影响 | 建议动作 |
| --- | --- | --- | --- | --- |

# 用户主链路诊断
## 链路重建
- 目标用户：
- 核心任务：
- 入口：
- 关键步骤：
- 成功结果：
- 回流或留存动作：

## 节点 1：<步骤名>
- PRD 现状：
- 关联原文：
> 原文摘录
- 缺失或问题：
- 为什么是问题：
- 对用户的影响：
- 建议补写：
- 建议补到 PRD 的位置：

## 节点 2：<步骤名>
...

# 状态与异常矩阵
| 链路节点 | 缺失状态 | 当前 PRD 是否覆盖 | 风险 | 建议补写 |
| --- | --- | --- | --- | --- |

# 交互与信息架构问题
- 问题 1：
  - 关联原文：
  - 风险级别：
  - 影响：
  - 建议：

# 业务规则与数据口径
- 规则冲突或缺失：
- 埋点或指标缺失：
- 实验或灰度验证缺失：

# AI 专项检查
仅在 PRD 明确涉及 AI 功能时输出本节。

- 输入约束：
- 输出不确定性：
- 失败兜底：
- 延迟与成本：
- 人工修正或接管：
- 评估指标：

# 建议补写清单
1. 补写：
   - 目的：
   - 应补内容：
2. 补写：
   - 目的：
   - 应补内容：

# 可直接带进评审会的问题列表
1. ...
2. ...
3. ...
```

## Finding Template

Use this format for important findings when a table is not enough:

```md
### [致命缺失] 结果页成功后缺少下一步路径
- 关联原文：
> “用户提交成功后显示成功提示”
- 问题：
PRD 只定义了成功提示，没有定义成功后的去向、可见收益或回流动作。
- 影响：
用户不知道下一步做什么，成功行为无法沉淀为留存或转化。
- 建议：
补充成功页结构，至少定义返回入口、下一步 CTA、是否自动跳转、是否展示关键收益。
- 建议补到：
“交互流程” 或 “页面说明” 章节。
```

## Writing Rules

- Put the verdict before the details.
- Tie major findings to a source excerpt, section title, or explicit omission.
- Separate fact from inference.
- Prefer precise edits over generic guidance.
- Avoid rewriting the whole PRD unless asked.
- If the PRD is thin, shrink the report and explicitly note the confidence limit.
