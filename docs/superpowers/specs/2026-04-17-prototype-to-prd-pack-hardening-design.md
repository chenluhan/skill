# prototype-to-prd-pack 第二版加固设计

## 结论

`prototype-to-prd-pack` 第一版已经证明方向成立，但交付闭环和输入稳定性都不够。

第二版的核心不是继续堆模板，而是修正两个根问题：

1. 自由输入缺少强约束中间层，导致结构化质量不稳定
2. 交付完成判定过于宽松，导致没有 SVG 和 PDF 时仍容易让用户误以为“已经完成”

第二版的默认策略应调整为：

- 用户仍然可以自由输入
- skill 内部必须先生成 `intake diagnosis`
- 所有输入都必须先进入受约束的中间层
- 所有生成结果都必须按交付等级判定，不再笼统宣称“生成成功”
- 对外保持一个 skill，对内区分 `full mode` 与 `delta mode`

## 为什么要改

第一版暴露的问题不是偶发 bug，而是系统设计上的偏差。

### 问题 1：导出链路只是“尽力而为”

当前 skill 会在 Markdown 与 JSON 生成成功后继续尝试 Mermaid 和 PDF。

这本身没有问题，但问题在于：

- Mermaid 渲染失败时，只留下 `.mmd`
- PDF 导出失败时，只留下 bundle
- 对用户的结果表达没有严格区分“结构化包完成”和“完整交付完成”

结果是用户很容易得到一种错误感受：

`文件好像生成了，但最终要的图和 PDF 并没有真的拿到。`

### 问题 2：自由输入没有被真正约束

第一版允许用户或 agent 直接组织 raw manifest，这降低了门槛，但也把结构正确性暴露给了用户。

对于不懂代码或不熟悉 schema 的用户，这会带来两个直接后果：

- 代码片段、字段名、数组结构很容易写错
- 错误直到生成链路后面才被发现，反馈过晚

这说明当前 skill 的系统承担复杂性仍然不够。

## 第二版目标

第二版必须做到四件事：

1. 自由输入仍可用，不要求用户掌握 schema
2. skill 内部必须把自由输入压成受约束的中间文件
3. 在生成前先明确告诉用户当前输入最多能产出到哪一级交付
4. 最终只能按交付等级汇报结果，不能再用含糊的“成功”描述
5. 当用户基于已有版本迭代时，能够只输出变化点，而不是重写整包

## 核心原则

### 1. 自由输入，内部强约束

对用户保持低门槛，对 skill 内部保持高约束。

### 2. 先诊断，再生成

不再默认直接进入 pack 生成，而是先输出一张 `intake diagnosis`。

### 3. 先判等级，再讲结果

不是先尝试所有步骤再说“失败了什么”，而是先判断当前输入和环境最多能达到的交付等级。

### 4. 缺依赖与缺材料必须区分

- 缺依赖：环境问题
- 缺材料：输入问题

这两类问题不能混在一起，否则用户无法判断下一步该补什么。

## 第二版工作流

第二版默认流程应调整为：

1. `detect_source`
2. `write_intake_diagnosis`
3. `write_raw_intake`
4. `validate_raw_intake`
5. `normalize_to_pack`
6. `validate_normalized_pack`
7. `build_pack`
8. `render_mermaid`
9. `export_pdf`
10. `write_delivery_status`

任何一步失败，都必须留下明确状态；后续步骤是否继续，取决于失败类型与目标交付等级。

## Intake Diagnosis 机制

### 目的

`intake diagnosis` 是第二版的默认起手式。

它不负责生成 PRD，而是负责先告诉用户：

- 当前识别到的输入来源是什么
- 当前证据强度足不足以生成完整交付
- 还缺什么最小材料
- 当前环境是否支持 Mermaid 和 PDF
- 本轮最多能做到哪一级交付

### 建议输出结构

固定输出为：

```markdown
# Intake Diagnosis

## Input Type
- ...

## Readiness
- Page reconstruction: High / Medium / Low
- Flow reconstruction: High / Medium / Low
- State and exception coverage: High / Medium / Low
- Mermaid source generation: Ready / Limited / Blocked
- SVG rendering: Ready / Blocked
- PDF export: Ready / Blocked

## Missing Materials
- ...

## Missing Dependencies
- ...

## Delivery Level This Round
- L1 / L2 / L3 / L4

## To Reach Next Level
- ...
```

### 作用

这个机制解决的是预期管理问题。

用户不再需要等到最后才知道：

- 为什么没出 SVG
- 为什么没出 PDF
- 为什么只能做半套

## 强约束中间层

### 总体结构

第二版必须固定三层中间文件：

```text
<run-dir>/
├── 00-intake-diagnosis.md
├── 01-raw-intake.json
├── 02-normalized-pack.json
├── 03-delivery-status.json
└── output/
    └── <project-name>-prd-pack/
```

### 00-intake-diagnosis.md

负责记录：

- 输入来源
- 当前可达成等级
- 缺失材料
- 缺失依赖
- 是否允许继续生成

### 01-raw-intake.json

这是用户自由输入被吸收后的第一个受约束容器。

它可以不完整，但字段名和结构必须受控。

它的目标不是最终正确，而是：

- 让自由输入先落进固定壳里
- 为后续 validator 提供统一入口

### 02-normalized-pack.json

这是后续所有脚本唯一允许读取的 canonical 文件。

从第二版开始：

- `build_pack.py` 只能吃这个文件
- `render_mermaid.sh` 只能读 pack 输出
- `export_pdf.sh` 只能读 pack 输出

不能再让后续步骤直接依赖用户原始文本、自由 code snippet 或零散聊天上下文。

### 03-delivery-status.json

这是每次运行的最终状态单。

它至少需要包含：

- `status`
- `achieved_level`
- `requested_level`
- `input_type`
- `blocking_issues`
- `missing_materials`
- `missing_dependencies`
- `generated_outputs`
- `next_actions`

## 双校验门设计

### 校验门 1：Raw Intake 校验

在 `01-raw-intake.json` 写好后，必须先过 intake validator。

它至少检查：

- 是否识别到输入来源
- 是否存在可识别页面或产物
- 是否存在基本证据摘要
- 是否能够判断当前可达成的交付等级

如果这一关不过，只能停在 diagnosis 阶段，不能继续生成 pack。

### 校验门 2：Normalized Pack 校验

在 `02-normalized-pack.json` 生成后，再过第二道校验。

它至少检查：

- page 对象字段是否完整
- flow 与 sequence 结构是否合法
- evidence 分类是否合法
- open questions 是否集中
- 是否具备生成目标交付等级所需的最小结构

如果这一关不过，不能进入 `build_pack`。

## 多来源 Intake 模板

第二版不应继续使用单一模板，而应采用：

`通用骨架 + 来源分支模板`

### 通用骨架字段

所有 `01-raw-intake.json` 都至少包含：

- `input_type`
- `project_name`
- `sources`
- `evidence_summary`
- `pages_or_artifacts`
- `flow_evidence`
- `state_evidence`
- `business_rule_evidence`
- `missing_materials`
- `user_notes`

### Figma Intake

建议最小输入：

- 文件或页面链接
- 关键 frame 或 screen 名称
- prototype 连线或页面顺序
- 页面备注

提示策略：

- 如果只有静态 frame，没有 prototype 连线，应明确提示流程图将降级为推断版
- 如果缺少 loading、empty、error frame，应明确提示状态矩阵只能部分补齐

### AI Studio Intake

建议最小输入：

- 原型链接
- 页面截图
- 页面切换关系
- 组件或模块说明

提示策略：

- 若只有截图没有页面跳转关系，应提示泳道流程图只能生成草案
- 若无字段说明，应提示表单校验和必填规则将进入待确认项

### HTML / 前端代码 Intake

建议最小输入：

- 可运行页面或核心页面代码
- 路由关系
- 表单与交互逻辑
- 状态处理代码或错误文案

提示策略：

- 只有 UI 结构没有逻辑时，应提示页面规格可生成，但状态与异常偏弱
- 缺少路由或事件处理时，应提示流程图只能覆盖页面结构，无法覆盖真实跳转

### 截图 / 图片 Intake

建议最小输入：

- 关键页面截图
- 页面顺序
- 每页用途
- 是否存在处理中、异常、空态截图

提示策略：

- 仅凭静态截图可以还原页面规格，但流程、状态和业务规则只能部分重建
- 缺少状态页截图时，异常、空态、加载态应进入待确认项

### 混合输入 Intake

建议最小输入：

- 各来源的主版本说明
- 主版本来源
- 是否存在时间差版本

提示策略：

- 若多来源未指定主版本，应提示页面与流程可能冲突
- 若截图与代码不一致，应默认以最新可运行产物或用户指定版本为准

## 提醒机制设计

提醒应分成三档，而不是给用户一份泛清单：

### 必须补

不补就无法进入生成。

### 建议补

不补可以生成，但只能到较低交付等级。

### 可选补

不影响生成，但会提升 PRD、流程图或 PDF 的质量。

### 话术要求

不再使用“请提供更多信息”这种空提醒。

应改为：

- 当前识别到的输入来源
- 当前可达成交付等级
- 想升到下一等级还缺什么
- 缺失会影响哪一类交付

例如：

`当前识别为截图输入。你现在可以生成 L1 结构化 PRD 包。若要生成质量更高的流程图，请补页面跳转关系或原型链接。`

## 双模式设计

第二版不建议拆出新的迭代 skill，而应保持：

- 对外：一个 skill
- 对内：两种运行模式

### Full Mode

用于首次从原型、截图、Figma、AI Studio 或 HTML 还原完整 PRD pack。

默认输出：

- 完整 Markdown pack
- JSON 资产
- Mermaid 源码
- 条件满足时再输出 SVG 和 PDF

### Delta Mode

用于用户基于既有版本继续迭代。

它的目标不是重写整包，而是：

- 识别这次改了什么
- 判断受影响范围
- 只输出变更点和受影响对象
- 仅在必要时再合并为完整最新版

### 为什么不拆 skill

如果现在拆成两个 skill，会立即带来三类问题：

- schema、模板、导出链路需要双份维护
- 用户会难以判断当前该用哪个 skill
- 首版与迭代版对 page、flow、rule、open question 的语义容易漂移

因此第二版的正确方向应是：

`一个 skill，双模式。`

## Delta Mode 设计

### 进入条件

满足任一条件时，优先进入 `delta mode`：

- 用户明确说“基于上一版改”
- 输入中包含旧版 pack、旧版 PRD 或旧版 normalized pack
- 用户明确说“只改这几个点”
- 输入中存在 baseline 版本标识

若没有基线，只能走 `full mode`。

此时应明确告知用户：

`当前缺少 baseline，只能重新生成 full pack，不能保证只输出新增点。`

### Delta Mode 的最小必要输入

第二版必须把 delta mode 的输入拆成两部分：

1. `baseline`
2. `change evidence`

#### baseline

至少需要以下之一：

- 旧版 pack 路径
- 旧版 `02-normalized-pack.json`
- 旧版可识别的 PRD / 结构化文档

#### change evidence

至少需要以下之一：

- 新截图
- 新原型链接
- 新 HTML / 页面代码
- 用户文字说明这次改了什么

如果只有 baseline，没有 change evidence，无法判断变化。  
如果只有 change evidence，没有 baseline，不能做稳定 delta，只能重跑 full mode。

### Delta Mode 中间文件

建议内部结构为：

```text
<run-dir>/
├── 00-intake-diagnosis.md
├── 01-change-intake.json
├── 02-impact-scope.json
├── 03-delivery-status.json
└── output/
    ├── delta/
    │   ├── 00-change-summary.md
    │   ├── 01-changed-pages.md
    │   ├── 02-changed-flows.md
    │   ├── 03-changed-rules.md
    │   ├── 04-open-questions-delta.md
    │   └── 05-ai-delta-spec.md
    └── merged/
        └── <project-name>-prd-pack/
```

### 01-change-intake.json

这个文件只记录本轮新增证据与用户声称的变化。

至少包含：

- `baseline_ref`
- `change_sources`
- `change_summary`
- `claimed_changes`
- `suspected_impacts`
- `missing_materials`

### 02-impact-scope.json

这是 delta mode 的核心约束文件。

它必须明确回答：

- 哪些页面受影响
- 哪些流程受影响
- 哪些规则受影响
- 哪些 open questions 被解决
- 哪些 open questions 新增
- 哪些对象明确不受影响

建议结构：

```json
{
  "baseline_ref": "",
  "change_scope": {
    "pages": [
      { "id": "home", "action": "update", "reason": "hero CTA changed" }
    ],
    "flows": [
      { "id": "submit-request", "action": "update", "reason": "new branch added" }
    ],
    "rules": [
      { "id": "login-before-submit", "action": "no_change" }
    ],
    "open_questions": [
      { "id": "sla", "action": "added" }
    ]
  },
  "unchanged_artifacts": ["request-status", "service-progress"],
  "merge_recommended": false
}
```

如果 `impact-scope.json` 没有写清，skill 不得继续生成 delta 文档。

### Delta 输出默认策略

第二版应把默认输出改为 `delta-only`。

默认输出：

- `00-change-summary.md`
- `01-changed-pages.md`
- `02-changed-flows.md`
- `03-changed-rules.md`
- `04-open-questions-delta.md`
- `05-ai-delta-spec.md`

硬规则：

`不重复输出未变化对象的完整内容。`

### 何时生成 merged full pack

默认不生成 merged full pack。

只有满足以下条件之一时才生成：

- 用户明确要求“给我合并后的完整最新版”
- 受影响页面、流程或规则超过阈值
- 主流程被重写
- `merge_recommended = true`

这条规则的目的，是防止模型每次一进入 delta mode 就重新输出整包。

### Delta Mode 用户反馈

delta mode 下的结果表达必须强调：

- 已识别 baseline
- 已识别受影响对象数量
- 其余内容默认沿用上一版
- 若要完整最新版，可额外生成 merged pack

例如：

`已识别到 baseline 版本。本轮检测到 2 个受影响页面、1 条受影响流程，其余内容默认沿用上一版。当前将先输出 delta pack；如需完整最新版，可继续生成 merged pack。`

### Delta Mode 的硬约束

第二版应增加以下约束：

1. 先比较 baseline，再写 delta
2. 没有 `impact-scope.json`，不得生成 delta 文档
3. delta 文档不得复制未变化对象的完整章节
4. merged full pack 不是默认产物，除非明确触发
5. 如果变化太大，应建议转为 full merge 或 full mode

## 交付等级判定

### 等级定义

第二版将交付分为五级：

- `L0 Blocked`
- `L1 Structured`
- `L2 Diagram Source`
- `L3 Visual Diagram`
- `L4 Full Delivery`

### 各级含义

#### L0 Blocked

intake 未通过，不能继续生成。

#### L1 Structured

已生成：

- Markdown 主文档
- JSON 结构化资产

但没有 Mermaid 源码或没有要求 Mermaid。

#### L2 Diagram Source

已生成：

- Markdown
- JSON
- `.mmd`

但没有 SVG。

#### L3 Visual Diagram

已生成：

- Markdown
- JSON
- `.mmd`
- `.svg`

但没有 PDF。

#### L4 Full Delivery

已生成：

- Markdown
- JSON
- `.mmd`
- `.svg`
- `.pdf`

### 完成判定硬规则

只有同时满足以下条件，才能宣告 `L4`：

- `00-overview.md` 到 `05-open-questions.md` 全部存在
- `assets/*.json` 存在
- `diagrams/*.mmd` 存在
- `diagrams/rendered/*.svg` 存在且数量符合预期
- `export/prd-pack.pdf` 存在

如果只生成了 Markdown 和 JSON，最多只能宣告 `L1`。

如果只额外生成了 Mermaid 源码，最多只能宣告 `L2`。

## 失败分类

第二版需要明确区分失败类型。

### Input Blocked

输入材料不足，无法进入生成。

例如：

- 无法识别页面
- 无法确认主版本
- 自由输入无法归一化

### Dependency Blocked

结构化包可生成，但环境缺依赖。

例如：

- 缺 `pandoc`
- 缺 Mermaid renderer
- 缺 PDF engine

### Quality Blocked

文件能生成，但质量达不到声明等级。

例如：

- 流程图数量不足
- 状态覆盖明显缺失
- 待确认项没有集中化

### Render Blocked

理论可导出，但实际渲染失败。

例如：

- Mermaid CLI 报错
- PDF engine 执行失败

## 依赖补齐策略

第二版原本只要求更早暴露依赖问题，但实际使用里这还不够。

如果 skill 每次都停在：

- `pandoc missing`
- `Mermaid renderer limited`

那用户拿到的仍然是“知道为什么失败”，而不是“以后不再失败”。

因此依赖策略需要继续收敛为：

### 1. 提供一次性 bootstrap 脚本

skill 内应新增显式依赖补齐脚本，例如：

- `scripts/bootstrap_dependencies.sh`

职责是：

- 检测 Homebrew、Node、npm 是否存在
- 安装稳定 Mermaid renderer
- 安装 `pandoc`
- 安装至少一个可用 PDF engine
- 安装完成后立即复检

### 2. 依赖选择优先级

在当前 macOS 环境下，优先选择：

- Mermaid: `mermaid-cli`，要求最终可用命令为 `mmdc`
- PDF export: `pandoc + weasyprint`

理由：

- `mmdc` 比 `npx` 首次安装更稳定，避免首次拉依赖时的长时间等待和偶发失败
- `pandoc + weasyprint` 可以让 PDF 导出成为本机常驻能力，而不是一次次停在 bundle
- 相比依赖更重或更不稳定的方案，这组组合更适合 skill 的长期复用

需要进一步补充为双平台策略：

#### macOS

推荐稳定组合：

- Node.js + `@mermaid-js/mermaid-cli`
- `pandoc + weasyprint`
- 优先复用本机 Chrome / Edge，而不是强依赖 Puppeteer 下载浏览器

原因：

- Mermaid 官方 npm 包比旧的 brew 安装路径更可信
- WeasyPrint 在 macOS 上可直接通过 Homebrew 获得

#### Windows

推荐把能力拆成两层：

- 流程图链路：Node.js + `@mermaid-js/mermaid-cli`
- PDF 链路：`pandoc + MiKTeX` 或官方 WeasyPrint / WSL 路径
- 若本机已有 Chrome / Edge，优先复用本机浏览器执行 Mermaid CLI

原因：

- Mermaid CLI 在 Windows 上可以直接通过 npm 安装，稳定性足够
- 复用本机浏览器可以减少 Puppeteer 下载阶段带来的慢、卡和中断风险
- WeasyPrint 官方对 Windows 的说明本身就是多步骤安装，不适合伪装成“一条命令一定成功”
- Pandoc 官方在 Windows 侧本来就推荐 MiKTeX 作为默认 PDF 路径，因此应把它作为可参考主链路之一

### 3. 安装行为边界

不建议每次运行 pack pipeline 时都隐式安装依赖。

正确边界是：

- 平时运行只检查和使用现有依赖
- 需要补环境时，显式运行 bootstrap 脚本
- bootstrap 脚本必须幂等，可重复执行

### 4. 用户可见表达

当 bootstrap 已存在时，对用户不应只说：

`请安装 pandoc。`

而应直接说：

`当前缺少 PDF 依赖。运行 scripts/bootstrap_dependencies.sh 可一次性补齐 Mermaid 与 PDF 导出依赖。`

并且要补充：

- 当前平台是什么
- 本平台推荐执行哪条 bootstrap 命令
- 如果 bootstrap 不能直接完成，参考文档在哪

也就是说，用户看到的不是笼统的“缺依赖”，而是：

- `当前平台：macOS`
- `可直接执行：bash scripts/bootstrap_dependencies.sh`

或：

- `当前平台：Windows`
- `可直接执行：powershell -ExecutionPolicy Bypass -File scripts\\bootstrap_dependencies.ps1`
- `若 PDF engine 仍未就绪，请按 references/dependency-setup.md 的 Windows 链路继续安装 MiKTeX 或官方 WeasyPrint/WSL 方案`

### 5. 平台支持表达

第二版需要新增一条硬规则：

`依赖诊断必须输出平台信息与平台特定下一步。`

至少应包含：

- `platform`
- `bootstrap_script`
- `bootstrap_command`
- `reference_guide`

### 6. Windows 边界

第二版不应对 Windows 做“假自动化”。

正确边界是：

- Mermaid CLI 与 Pandoc 可以提供直接安装脚本
- PDF engine 若使用 MiKTeX 或原生 WeasyPrint，允许脚本先帮用户装一部分，再把剩余官方步骤明确告诉用户
- 如果当前环境更适合 WSL，也要把 WSL 作为显式备选链路写进参考文档

### 7. 成功标准补充

依赖策略落地后，应新增一个成功标准：

`在已运行 bootstrap 的机器上，full mode 与 delta mode 默认都应具备稳定导出 PDF 的能力，而不是长期停留在 L3。`

## 用户可见结果表达

第二版必须停止使用模糊的“生成成功，但 PDF 没有”。

建议改为固定结果格式：

```markdown
验证结果：
- 当前交付等级：L2 Diagram Source
- 未达到目标等级：L4 Full Delivery

原因：
- SVG 未生成：Mermaid renderer 不可用或首次依赖安装未完成
- PDF 未生成：本机缺少 pandoc

现在最值得先看的：
- 01-prd.md
- 02-pages.md
- 05-open-questions.md

要升到下一等级：
- 安装 Mermaid renderer，重新执行 render_mermaid
- 安装 pandoc 与 PDF engine，重新执行 export_pdf
```

## 对现有 skill 的影响

第二版不是轻微补丁，而是以下方向上的收紧：

1. `SKILL.md` 必须改写为 intake-first 流程
2. 需要新增 `validate_manifest.py`
3. 需要新增导出前置预检能力
4. 需要新增 `03-delivery-status.json`
5. 需要把用户提醒逻辑写进 workflow，而不是留给 agent 自由发挥

## 非目标

第二版不试图解决以下问题：

- 一次性兼容所有原型工具的深度 API 集成
- 让用户完全不需要补任何材料就稳定生成 L4

第二版的目标不是“无条件完成”，而是：

`更早判断、更清楚告知、更准确分级、更稳定出包。`

## 成功标准

第二版设计完成后，应至少满足：

1. 用户给自由输入时，不需要自己理解 schema
2. skill 能先输出 intake diagnosis，而不是直接开始写 PRD
3. skill 能明确区分缺材料与缺依赖
4. 没有 SVG 和 PDF 时，不再错误宣告完整交付
5. 用户可以清楚知道当前等级、缺口和下一步动作

## 当前判断

第二版的正确方向已经明确：

- 采用 `自由输入 + 强约束中间层`
- 默认先生成 `intake diagnosis`
- 按来源模板做提醒
- 按交付等级做完成判定
- 保持一个 skill，但增加 `full mode` 与 `delta mode`
- 在 delta mode 中以 baseline 与 impact scope 约束“只输出变化点”

这版设计确认后，再进入 skill 实现，才是合理顺序。
