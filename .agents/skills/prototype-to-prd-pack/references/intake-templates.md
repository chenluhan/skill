# Intake Templates

Use these reminders when building `00-intake-diagnosis.md`.

## Figma

### Best inputs

- File or page link
- Key frames or screen names
- Prototype connections or page order
- Notes on loading, empty, and error states

### Reminder style

- `当前识别为 Figma 输入。`
- `若只有静态 frame，没有 prototype 连线，流程图将降级为推断版。`
- `若缺少 loading、empty、error frame，状态矩阵只能部分补齐。`

## AI Studio

### Best inputs

- Prototype link
- Screen captures
- Page transition logic
- Component or module notes

### Reminder style

- `当前识别为 AI Studio 输入。`
- `若只有截图，没有页面切换关系，泳道流程图只能生成草案。`
- `若没有字段说明，表单校验与必填规则将进入待确认项。`

## HTML or Frontend Code

### Best inputs

- Runnable page or source files
- Routing map
- Form and interaction logic
- Error-state copy or state handlers

### Reminder style

- `当前识别为 HTML / 前端代码输入。`
- `页面结构证据足够，但若缺少状态逻辑，异常与状态矩阵会明显偏弱。`
- `若无路由或事件处理，流程图只能覆盖页面结构，不能覆盖真实跳转。`

## Screenshots

### Best inputs

- Key screen captures
- Screen order
- Purpose of each screen
- Loading, empty, processing, and error screenshots when available

### Reminder style

- `当前识别为截图输入。`
- `你现在可以生成结构化 PRD 包，但若要提高流程图质量，请补页面跳转关系或原型链接。`
- `缺少状态页截图时，异常、空态、加载态会进入待确认项。`

## Mixed Inputs

### Best inputs

- Main source of truth
- Which source is newer
- Which source covers flow vs page detail

### Reminder style

- `当前识别为混合输入。`
- `请指定主版本来源，否则页面与流程可能冲突。`
- `若截图与代码不一致，默认以最新可运行产物或你指定版本为准。`
