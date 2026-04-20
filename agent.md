# /Users/apple/Desktop/skill 工作约定

## 目标
- 这个目录是 Codex `skill` 与后续 `agent` 的源码仓库。
- 这个目录同时承担两件事：一是 skill 的分类与分发仓库，二是后续 agent 资产仓库。
- 当前阶段，本地运行目录仍是主要创作入口；这个仓库负责镜像、分类、归档与远端分发。
- `git` 负责记录正式变更，并将可分发内容同步到远端仓库。

## 目录规则
- `.agents/skills/<skill-name>/`：本地 skill 镜像后的 repo 副本，是对外分发入口。
- `.claude/skills/<skill-name>`：指向 `.agents/skills/<skill-name>/` 的兼容入口；由脚本生成，不直接编辑。
- `catalog/`：skill 分类规则与清单索引。
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
- 新增或修改 skill 时，优先继续在当前本地运行目录中完成；再由同步脚本镜像进仓库。
- 仓库中的 `.agents/skills/`、`.claude/skills/` 与 `catalog/skills-index.md` 都由同步脚本维护。
- 自动同步只允许提交 skill 分发相关路径，不得顺带提交仓库里的其他改动。
- 正式 agent 内容放进 `agents/`；设计与脚本分别放进 `docs/`、`scripts/`；临时产物留在 `notes/`。
- 如果未来要切换到 repo-first 工作流，先更新本文档，再把本地运行目录替换成指向 repo 的软链接。

## Git 规则
- 自动同步的定义是：先镜像本地 skill、重建分类索引，再自动 `add`、创建本地提交，并在凭证可用时发布到 `origin/main`。
- 这个仓库允许自动 `git push`，因为远端仓库本身就是 skill 分发入口；其他仓库仍默认不自动推送。
- 手动提交与自动提交的 message 都使用英文，简洁描述变更意图。

## 验证规则
- 修改 skill 后，优先运行该 skill 自带的代表性校验脚本。
- 没有自动校验脚本时，至少检查结构是否满足 `SKILL.md` 必需约定。
- 每次同步后，必须确认 `.claude/skills/` 兼容入口与 `catalog/skills-index.md` 已更新。
- 无法验证的项，需要在提交说明或对话里明确原因。
