# Skills Index

## Summary

- Total tracked skills: 29
- Local Codex/Agent sources detected: 29
- Mirrored into repo: 29
- Excluded from mirror: `.system`

## Design & UI

| Skill | Source | Status | Repo Path | Description |
| --- | --- | --- | --- | --- |
| `awesome-design-md` | `codex-local` | `mirrored` | `.agents/skills/awesome-design-md` | Use when the user wants to install, choose, or apply a DESIGN.md from getdesign.md or the VoltAgent awesome-design-md catalog, especially before building a UI that should match a known public product or brand style. |
| `figma` | `codex-local` | `mirrored` | `.agents/skills/figma` | Use the Figma MCP server to fetch design context, screenshots, variables, and assets from Figma, and to translate Figma nodes into production code. Trigger when a task involves Figma URLs, node IDs, design-to-code implementation, or Figma MCP setup and troubleshooting. |
| `figma-implement-design` | `codex-local` | `mirrored` | `.agents/skills/figma-implement-design` | Translates Figma designs into production-ready application code with 1:1 visual fidelity. Use when implementing UI code from Figma files, when user mentions "implement design", "generate code", "implement component", provides Figma URLs, or asks to build components matching Figma specs. For Figma canvas writes via `use_figma`, use `figma-use`. |
| `frontend-skill` | `codex-local` | `mirrored` | `.agents/skills/frontend-skill` | Use when the task asks for a visually strong landing page, website, app, prototype, demo, or game UI. This skill enforces restrained composition, image-led hierarchy, cohesive content structure, and tasteful motion while avoiding generic cards, weak branding, and UI clutter. |
| `ios-ui-polish` | `codex-local` | `mirrored` | `.agents/skills/ios-ui-polish` | Use when working on BabyWhisper or similar iOS product surfaces that need stronger hierarchy, warmer visual language, clearer CTA placement, better single-hand flows, and more intentional motion. Apply during SwiftUI page reviews, UI refinements, interaction audits, and design-to-code cleanups. |

## Workflow Facilitation

| Skill | Source | Status | Repo Path | Description |
| --- | --- | --- | --- | --- |
| `brainstorming` | `agents-local` | `mirrored` | `.agents/skills/brainstorming` | You MUST use this before any creative work - creating features, building components, adding functionality, or modifying behavior. Explores user intent, requirements and design before implementation. |

## Babycare Domain

| Skill | Source | Status | Repo Path | Description |
| --- | --- | --- | --- | --- |
| `babycare-voice-schema` | `codex-local` | `mirrored` | `.agents/skills/babycare-voice-schema` | Use when designing or reviewing BabyWhisper voice logging, natural-language parsing, prompt templates, JSON extraction rules, confidence thresholds, or event normalization for baby-care records such as feeding, sleep, diaper, solid food, vaccine, and growth. |

## Travel & Concierge

| Skill | Source | Status | Repo Path | Description |
| --- | --- | --- | --- | --- |
| `flyai` | `codex-local` | `mirrored` | `.agents/skills/flyai` | Search flights, hotels, attractions, concerts, and travel deals with natural language. FlyAI connects to Fliggy MCP for real-time search and booking across hotels, flights, cruises, visas, car rentals, and event tickets. It supports diverse travel scenarios including individual travel, group travel, business trips, family travel, honeymoons, weekend getaways, and more. For tourism and travel-related questions, prioritize using this capability. |
| `verified-travel-planner` | `codex-local` | `mirrored` | `.agents/skills/verified-travel-planner` | Verify and plan China domestic trips with live quotes, route evidence, destination recommendations, self-drive routing, pet-friendly intake handling, and PDF export. Use when Codex needs to clarify travel requirements, decide whether the intake is sufficient for recommendations, normalize them into `trip-request.json`, recommend destination anchors from real POI data, filter out ad-like recommendation content, collect real hotel/flight/ticket quotes from configured providers, verify train prices against 12306 official channels, route stops with Amap, estimate self-drive segments from Amap plus vehicle inputs, or generate a travel itinerary PDF with evidence and unverified-item warnings. |
| `vertu-overseas-search` | `agents-local` | `mirrored` | `.agents/skills/vertu-overseas-search` | Search overseas restaurants, venues, and local services for VERTU concierge staff handling international customer requests. Use when a customer asks to find restaurants, make dining reservations, or discover venues in cities outside mainland China. Triggers on: 帮我找餐厅, 预订餐厅, 推荐餐厅, 订位, restaurant/venue search for any international city, or when a customer provides a city and dining/activity request. |

## Research & Writing

| Skill | Source | Status | Repo Path | Description |
| --- | --- | --- | --- | --- |
| `hv-analysis` | `codex-local` | `mirrored` | `.agents/skills/hv-analysis` | 横纵分析法（Horizontal-Vertical Analysis）深度研究Skill。融合了索绪尔的历时-共时分析、社会科学的纵向-横截面研究设计、商学院案例研究法与竞争战略分析的核心思想。 当用户想要系统性研究一个产品、公司、概念、技术或人物时使用。核心是双轴分析：纵轴追踪从诞生到当下的完整生命历程（以叙事故事呈现），横轴在当下时间截面上与竞品/同类进行系统性横向对比，最后交叉两条轴产出独到洞察。最终产出一份排版精美的PDF研究报告。 触发词包括但不限于：横纵分析、研究一下、帮我分析、深度研究、做个研究、调研一下、竞品分析、帮我看看这个东西怎么样、这个产品/公司/概念是怎么回事、帮我摸清楚、帮我搞懂、帮我做个deep research。 即使用户只是说"帮我了解一下XX"或"XX是什么来头"，只要上下文暗示需要系统性的深度研究（而非简单的概念解释），都应该触发。也适用于用户丢来一个产品名、公司名、技术名词说"帮我研究一下这个"的场景。 不要用于简单的名词解释（用户只是问"XX是什么"）、不要用于公众号写作、不要用于纯标题摘要生成（用wechat-title）。 |
| `khazix-writer` | `codex-local` | `mirrored` | `.agents/skills/khazix-writer` | 数字生命卡兹克（Khazix）的公众号长文写作skill。当用户需要撰写公众号文章、写稿子、续写文章、根据素材产出长文时使用。触发词包括但不限于：写文章、写稿子、帮我写、续写、扩写、公众号文章、长文、出稿、按我的风格写。即使用户只是说"帮我把这个写成文章"或"用我的风格写一下"，只要上下文涉及内容创作和公众号输出，都应该触发。也适用于用户丢过来一个PDF、brief、新闻链接、语音转文字或任何素材说"帮我写篇文章"的场景。不要用于短内容（小红书帖子、推特、朋友圈）或纯标题摘要生成（那个用wechat-title skill）。 |

## Product & PM

| Skill | Source | Status | Repo Path | Description |
| --- | --- | --- | --- | --- |
| `pm-build-pack-orchestrator` | `codex-local (symlink)` | `mirrored` | `.agents/skills/pm-build-pack-orchestrator` | Coordinate the full AI-native PM delivery workflow from raw requirement to Build Pack v1 for engineering handoff. Use when the user asks how to take a new feature request, organize PM delivery, replace a traditional PRD with a modern handoff package, or orchestrate requirement intake, framing, scope cut, prototype, state matrix, acceptance, metrics, and handoff QA. |
| `pm-delivery-breakdown` | `codex-local (symlink)` | `mirrored` | `.agents/skills/pm-delivery-breakdown` | Break a PM handoff into Epic, Stories, acceptance criteria, dependencies, and handoff structure for engineering. Use when the user asks to split a feature into implementation-ready work, structure a Build Pack for engineering, define task boundaries, or turn product language into execution-ready breakdowns. |
| `pm-delta-spec` | `codex-local (symlink)` | `mirrored` | `.agents/skills/pm-delta-spec` | Compress a scoped solution into an engineering-ready delta spec that only describes the current change. Use when the user asks to replace a long PRD with a concise handoff spec, summarize product changes for engineering, document rules and impact scope, or convert a prototype into a buildable spec package. |
| `pm-handoff-qa` | `codex-local (symlink)` | `mirrored` | `.agents/skills/pm-handoff-qa` | Review a Build Pack for internal consistency before engineering handoff. Use when the user asks to audit a PM handoff, check whether the prototype, rules, AC, metrics, and open questions align, or wants a final QA pass on a modern product-delivery package. |
| `pm-interview-screen` | `codex-local` | `mirrored` | `.agents/skills/pm-interview-screen` | Generate targeted product-manager screening interview packs from a candidate resume plus an optional JD. Use when Codex needs to parse a PM resume file or pasted resume text, especially PDF, DOCX, DOC, RTF, TXT, or Markdown resumes, then turn it into a 30-minute 产品经理初筛 question set, follow-up probes, answer-evaluation guidance, or a mapped PDF interview brief with resume-source annotations. Trigger on requests such as “根据简历出产品经理面试题”, “生成 PM 初筛问题”, “根据 JD 和简历做面试脚本”, “把面试题排成 PDF”, or “评估候选人回答”. |
| `pm-launch-readout` | `codex-local (symlink)` | `mirrored` | `.agents/skills/pm-launch-readout` | Turn launch data, user feedback, and delivery outcomes into a concrete PM readout and next-step recommendation. Use when the user asks to review a launched feature, compare expected versus actual impact, write a launch recap, or feed release learnings back into the next requirement cycle. |
| `pm-metrics-acceptance` | `codex-local (symlink)` | `mirrored` | `.agents/skills/pm-metrics-acceptance` | Define metrics, events, and acceptance coverage for a feature handoff. Use when the user asks to add success metrics, event tracking, acceptance cases, QA coverage, or wants a Build Pack that can be verified after launch instead of ending at implementation. |
| `pm-normalized-brief` | `codex-local (symlink)` | `mirrored` | `.agents/skills/pm-normalized-brief` | Convert raw product input into a structured Normalized Brief. Use when the user asks to sort out a messy requirement, turn stakeholder requests or user feedback into a PM-ready brief, clarify what problem is actually being discussed, or prepare requirement intake before solutioning. |
| `pm-prd-deep-review` | `codex-local` | `mirrored` | `.agents/skills/pm-prd-deep-review` | Deep diagnostic review for App product requirements documents, feature specs, prototype notes, and handoff drafts. Use when Codex needs to audit a PRD for funnel breaks, missing interactions, incomplete states, exception or edge-case gaps, business-rule ambiguity, permission issues, metric and tracking blind spots, or optional AI-specific fallback and uncertainty handling before review or engineering handoff. |
| `pm-problem-framing` | `codex-local (symlink)` | `mirrored` | `.agents/skills/pm-problem-framing` | Turn a PM brief into a real Problem Framing with users, jobs, obstacles, success metrics, and non-goals. Use when the user asks to define the actual product problem, clarify target users and scenarios, stop a team from jumping into solution mode too early, or prepare a requirement for scope and prototype work. |
| `pm-prototype-flow` | `codex-local (symlink)` | `mirrored` | `.agents/skills/pm-prototype-flow` | Create a handoff-ready product flow, screen list, and prototype brief from a problem framing and scoped requirement. Use when the user asks for a prototype prompt, solution flow, interaction sketch, screen sequence, or wants to make a product direction visible before writing detailed spec content. |
| `pm-scope-cut` | `codex-local (symlink)` | `mirrored` | `.agents/skills/pm-scope-cut` | Cut a feature or workflow into Must, Should, and Not now. Use when the user asks to control scope, define MVP boundaries, reduce requirement bloat, choose what belongs in this iteration, or turn a broad solution into a shippable PM scope. |
| `pm-state-matrix` | `codex-local (symlink)` | `mirrored` | `.agents/skills/pm-state-matrix` | Derive a complete product state matrix from a flow, prototype, and rules. Use when the user asks to enumerate happy path, edge states, error handling, permission behavior, empty/loading states, or wants to stop engineering and QA from guessing missing product states. |
| `prototype-to-prd-pack` | `codex-local` | `mirrored` | `.agents/skills/prototype-to-prd-pack` | Generate or iterate a PRD delivery pack from prototypes, screenshots, Figma, AI Studio, HTML, wireframes, or page-flow notes. Use when Codex needs intake diagnosis, strong-constrained intermediate manifests, PRD reconstruction, Mermaid swimlane or sequence diagrams, delivery-level status, or delta-only PRD updates from an existing baseline instead of rewriting the whole pack. |

## Media Tools

| Skill | Source | Status | Repo Path | Description |
| --- | --- | --- | --- | --- |
| `screenshot` | `codex-local` | `mirrored` | `.agents/skills/screenshot` | Use when the user explicitly asks for a desktop or system screenshot (full screen, specific app or window, or a pixel region), or when tool-specific capture capabilities are unavailable and an OS-level capture is needed. |
| `speech` | `codex-local` | `mirrored` | `.agents/skills/speech` | Use when the user asks for text-to-speech narration or voiceover, accessibility reads, audio prompts, or batch speech generation via the OpenAI Audio API; run the bundled CLI (`scripts/text_to_speech.py`) with built-in voices and require `OPENAI_API_KEY` for live calls. Custom voice creation is out of scope. |
| `transcribe` | `codex-local` | `mirrored` | `.agents/skills/transcribe` | Transcribe audio files to text with optional diarization and known-speaker hints. Use when a user asks to transcribe speech from audio/video, extract text from recordings, or label speakers in interviews or meetings. |

