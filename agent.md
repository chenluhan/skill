# /Users/apple/Desktop/skill 工作约定

## 目标
- 这个目录是 Codex `skill` 与后续 `agent` 的源码仓库。
- 仓库内文件是唯一事实来源；运行目录里的副本、软链接或安装产物不作为主编辑对象。
- `git` 负责记录正式变更；自动同步只做本地 `commit`，不自动 `push`。

## 目录规则
- `skills/<skill-name>/`：正式 skill 源码。每个 skill 至少包含 `SKILL.md`，可按需包含 `references/`、`scripts/`、`assets/`。
- `agents/<agent-name>/`：后续 agent 的提示词、配置、说明与辅助资源。
- `docs/superpowers/specs/`：设计文档与规格说明。
- `notes/`：临时分析、运行产物、调试输出；默认不纳入版本控制，可随任务结束清理。
- `scripts/`：仓库维护脚本，例如 git 自动提交脚本。
- 根目录只保留 `agent.md`、`.gitignore` 与少量必须人工快速查看的仓库文件。

## 命名规则
- skill 与 agent 名称使用小写加中划线，例如 `pm-prd-deep-review`。
- 设计文档命名为 `YYYY-MM-DD-<topic>-design.md`。
- 脚本文件名使用英文小写加中划线。

## 工作流程
- 先定规则，再动结构；规则变化先改本文档，再改目录与脚本。
- 新增 skill 或 agent 时，先在 `docs/superpowers/specs/` 写设计或 delta 说明，再落正式源码。
- 正式内容只放进 `skills/`、`agents/`、`docs/`、`scripts/`；临时产物留在 `notes/`。
- 若需要让 Codex 直接使用仓库里的 skill，优先从运行目录指向仓库源码，而不是双向复制。

## Git 规则
- 自动同步的定义是：检测工作区变更，自动 `add` 并创建本地提交。
- 自动流程禁止执行 `git push`。
- 手动提交与自动提交的 message 都使用英文，简洁描述变更意图。

## 验证规则
- 修改 skill 后，优先运行该 skill 自带的代表性校验脚本。
- 没有自动校验脚本时，至少检查结构是否满足 `SKILL.md` 必需约定。
- 无法验证的项，需要在提交说明或对话里明确原因。
