**语言：** [English](README.md) | **简体中文**

# Simulink Automation Suite

![Claude Code Plugin](https://img.shields.io/badge/Claude_Code-Plugin-4A5568)
![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![MATLAB](https://img.shields.io/badge/MATLAB-Engine-orange)

Simulink Automation Suite 是一个基于 MATLAB Engine for Python 的 Claude Code 插件，用于 Simulink 自动化分析与参数修改流程。

- 插件标准名称：`simulink-automation-suite`
- 已发布技能：`simulink-scan`（只读分析）、`simulink-edit`（参数修改）
- 运行时 Python 模块路径：`simulink_cli`（统一 CLI 入口）

---

## 工具定位

Simulink Automation Suite 的核心定位，是让 Simulink 分析能力在 Claude Code 中具备 Agent 原生可调用性：

- 以确定性、机器可读的结果暴露模型上下文。
- 让 AI 基于真实模型拓扑与参数进行分析，而不是仅凭截图理解。
- 通过裁剪与字段投影控制输出体积，兼顾实时性与 token 成本。

一句话：先让 AI 读懂模型，再让 AI 辅助开发分析。

![工具定位图](docs/assets/readme/positioning-ai-plugin-simulink.png)

---

## 为什么需要这个插件

常见的 AI+Simulink 使用方式通常是这两类：

1. 截图问答：接入快，但理解深度受限，且依赖视觉能力。
2. 导出后解析：信息更完整，但流程重、反馈慢、token 开销高。

这个插件提供第三条路径：让 Agent 直接基于结构化、可运行时调用的模型能力完成分析。

![能力总览图](docs/assets/readme/capability-overview.png)

---

## 工作方式

1. Claude Code 在 Simulink 分析场景下调用 `simulink-scan` 技能。
2. 技能先解析 MATLAB 会话上下文（`session list/use/current/clear`），并使用精确会话名匹配；当存在多个会话时，可通过显式 `--session` 或预先选择的 active session 解析目标会话。
3. 然后执行核心动作之一：`schema`、`list_opened`、`scan`、`connections`、`inspect`、`find`、`highlight`。
4. 结果通过 `stdout` 输出为单一机器可读 JSON 负载；原始警告文本不会直接污染 stdout。
5. 异常通过稳定错误码返回，便于 Agent 做恢复重试。
6. 对于参数修改场景，Claude Code 会调用 `simulink-edit` 技能。
7. 编辑技能通过 `set_param` 提供预览模式（默认开启 dry-run）、机器可回放的 `apply_payload`、基于 `expected_current_value` 的 guarded execute、回滚负载与写后读回验证。

---

## 前置条件

在使用依赖 MATLAB 会话的动作（`list_opened`、`scan`、`connections`、`inspect`、`find`、`highlight`）前，请先确认：

1. 本机已安装并可启动 MATLAB。
2. 当前插件使用的 Python 解释器中已安装 MATLAB Engine for Python。
3. 在 MATLAB 命令窗口执行：

```matlab
matlab.engine.shareEngine
```

排障指引：

- `engine_unavailable`：当前 Python 环境不可用 MATLAB Engine for Python，请先修复解释器环境安装。
- `no_session`：MATLAB Engine 可用，但没有共享会话，请在 MATLAB 中执行 `matlab.engine.shareEngine` 后重试。

---

## 快速开始

### 1. 添加 Marketplace 源

```bash
/plugin marketplace add Mistakey/simulink-automation-suite
```

### 2. 从 Marketplace 安装插件

```bash
/plugin install simulink-automation-suite@simulink-automation-marketplace
```

### 3. 通过命名空间调用技能

```text
/simulink-automation-suite:simulink-scan Scan gmp_pmsm_sensored_sil_mdl recursively and focus on controller subsystems.
```

### 4. 校验插件注册（可选）

```bash
/plugin list simulink-automation-suite@simulink-automation-marketplace
```

---

## 使用示例（跳转）

完整的 Claude Code Prompt 示例与截图已放在单独页面（中英合并，避免 README 过重）：

- [docs/examples/claude-code-scenarios.md](docs/examples/claude-code-scenarios.md)

---

## 核心动作

| 动作 | 用途 | 示例 |
|---|---|---|
| `schema` | 返回机器可读的命令契约 | `python -m simulink_cli schema` |
| `list_opened` | 列出当前已打开的 Simulink 模型 | `python -m simulink_cli list_opened` |
| `scan` | 读取模型/子系统拓扑结构 | `python -m simulink_cli scan --model "my_model" --recursive` |
| `connections` | 读取目标模块的上游/下游关键连接模块 | `python -m simulink_cli connections --target "my_model/Gain" --direction both --depth 1 --detail summary` |
| `inspect` | 读取模块参数和有效值 | `python -m simulink_cli inspect --model "my_model" --target "my_model/Gain" --param "All"` |
| `highlight` | 在 Simulink 中高亮目标模块（仅 UI 定位，不修改模型） | `python -m simulink_cli highlight --target "my_model/Gain"` |
| `find` | 按名称模式和/或模块类型搜索模块 | `python -m simulink_cli find --model "my_model" --name "PID"` |
| `set_param` | 设置模块参数（支持预览与回滚） | `python -m simulink_cli set_param --target "my_model/Gain1" --param "Gain" --value "2.0"` |
| `session` | 管理或选择当前 MATLAB 共享会话 | `python -m simulink_cli session list` |

---

## 输出控制

当需要更紧凑的返回结果时，可使用截断与字段投影参数：

```bash
python -m simulink_cli scan --model "my_model" --max-blocks 200 --fields "name,type"
python -m simulink_cli inspect --model "my_model" --target "my_model/Gain" --param "All" --max-params 50 --fields "target,values"
python -m simulink_cli connections --target "my_model/Gain" --detail ports --max-edges 50 --fields "target,edges,total_edges,truncated"
python -m simulink_cli find --model "my_model" --name "PID" --max-results 50 --fields "path,type"
```

---

## JSON 请求模式

`--json` 是一等入口，且与基于参数的动作调用互斥。
`schema` 返回结构化字段元数据（类型、必填/默认值/枚举、字段说明）。
对于复杂字符串和换行，JSON 请求模式是规范入口；只要值里包含需要转义的内容，优先使用 `--json`。

```bash
python -m simulink_cli --json "{\"action\":\"schema\"}"
python -m simulink_cli --json "{\"action\":\"list_opened\",\"session\":\"MATLAB_12345\"}"
python -m simulink_cli --json "{\"action\":\"scan\",\"model\":\"my_model\",\"recursive\":true,\"session\":\"MATLAB_12345\"}"
python -m simulink_cli --json "{\"action\":\"inspect\",\"model\":\"my_model\",\"target\":\"my_model/Gain\",\"param\":\"Description\",\"summary\":true}"
python -m simulink_cli --json '{"action":"connections","target":"my_model/Gain","direction":"both","depth":1,"detail":"summary","max_edges":50,"fields":["target","upstream_blocks","downstream_blocks"]}'
python -m simulink_cli --json '{"action":"find","model":"my_model","name":"PID","max_results":50,"fields":["path","type"]}'
python -m simulink_cli --json '{"action":"set_param","target":"my_model/Gain1","param":"Gain","value":"2.0"}'
```

---

## 安全模型（simulink-edit）

- `dry_run` 默认为 `true`，并返回 `rollback` 与机器可回放的 `apply_payload`
- `apply_payload` 会携带 `expected_current_value`，用于在 execute 时拒绝过期预览
- 执行时应直接回放返回的 `apply_payload`，不要手工重建 guarded execute 负载
- 如果预览已经过期，回放会返回 `precondition_failed`，且不会误改模型
- 执行模式会读回参数值以验证写入结果
- 如果读回值无法证明写入成功，动作会返回 `verification_failed`，并保留回滚与恢复元数据
- 每次响应都包含 `rollback` 负载，支持一条命令撤销；如果原请求显式指定了会话，回滚负载会保留该会话信息
- `value` 字段始终按字符串传递，并且可以合法包含 `%`，例如 `"%.3f"`
- 每次调用只修改一个参数（不支持批量操作）

## Guarded Edit Loop

标准的单参数 Agent 编辑回路是：

1. 先用 `inspect` 确认当前参数状态。
2. 运行 `set_param` 且 `dry_run=true`。
3. 原样回放返回的 `apply_payload`。
4. 再次 `inspect` 确认新值。
5. 如需恢复，原样回放 `rollback`。

预览响应示例：

```json
{
  "action": "set_param",
  "dry_run": true,
  "current_value": "1.5",
  "proposed_value": "2.0",
  "apply_payload": {
    "action": "set_param",
    "target": "my_model/Gain1",
    "param": "Gain",
    "value": "2.0",
    "dry_run": false,
    "expected_current_value": "1.5"
  },
  "rollback": {
    "action": "set_param",
    "target": "my_model/Gain1",
    "param": "Gain",
    "value": "1.5",
    "dry_run": false
  }
}
```

如果目标在 preview 和 execute 之间发生变化，回放这份保存下来的 `apply_payload` 会返回 `precondition_failed`；如果写入执行了但读回验证未确认成功，则会返回 `verification_failed`。

---

## 严格默认行为与错误契约

- 会话匹配仅支持精确匹配（不支持模糊匹配）。
- 当 MATLAB 共享会话多于一个时，涉及 MATLAB 连接的动作必须先通过 `session use <name>` 选定会话，或显式传 `--session`。
- 当无法从当前会话解析出活动模型根时，`scan` 和 `find` 会稳定返回 `model_not_found`。
- `unknown_parameter` 表示调用方传入了不属于契约的请求字段或命令参数。
- `param_not_found` 表示目标模块并未暴露请求的运行时参数。
- JSON 非法或字段类型错误会返回 `invalid_json`。

错误返回结构：

```json
{
  "error": "<stable_code>",
  "message": "<human_readable_message>",
  "details": {},
  "suggested_fix": "<optional_next_step>"
}
```

常见错误码：

- `invalid_input`
- `invalid_json`
- `unknown_parameter`
- `json_conflict`
- `engine_unavailable`
- `no_session`
- `session_required`
- `session_not_found`
- `state_write_failed`
- `state_clear_failed`
- `model_required`
- `model_not_found`
- `subsystem_not_found`
- `invalid_subsystem_type`
- `block_not_found`
- `param_not_found`
- `precondition_failed`
- `set_param_failed`
- `verification_failed`
- `inactive_parameter`
- `runtime_error`

当本地插件状态文件不可写时，`session use` / `session clear` 可能返回 `state_write_failed` 或 `state_clear_failed`。

如果没有可用 MATLAB 共享会话，请先在 MATLAB 中执行 `matlab.engine.shareEngine` 再重试。

---

## 仓库内容

```text
simulink_cli/           # 统一 CLI 包（单一入口）
├── __main__.py         # python -m simulink_cli
├── core.py             # Action 注册、JSON/flag 解析、schema、路由
├── errors.py           # 错误信封构建器
├── json_io.py          # JSON I/O 工具
├── validation.py       # 输入校验
├── session.py          # MATLAB 会话管理
├── model_helpers.py    # 路径解析辅助
└── actions/            # 每个 action 一个模块
    ├── scan.py
    ├── inspect_block.py
    ├── connections.py
    ├── find.py
    ├── highlight.py
    ├── list_opened.py
    ├── set_param.py
    └── session_cmd.py
skills/                 # 插件技能定义（仅文档，无 Python 代码）
├── simulink_scan/      # 只读分析技能
│   ├── SKILL.md
│   ├── reference.md
│   └── test-scenarios.md
└── simulink_edit/      # 参数修改技能
    ├── SKILL.md
    ├── reference.md
    └── test-scenarios.md
tests/                  # 测试套件
```

---

## 验证

```bash
python -m unittest discover -s tests -p "test_*.py" -v
claude plugin validate .
```

---

## 路线图

- **当前阶段（v2.0.x）：** 在只读分析基础上新增 guarded 参数修改能力（`set_param`，支持 dry-run 预览、`apply_payload`、回滚、前置条件检查与写后验证），通过统一的 `simulink_cli` 包同时服务 `simulink-scan` 和 `simulink-edit` 技能。
- **下一阶段：** 在保持可预测契约与恢复链路的前提下，增强 Agent 工作流编排与可靠性。
- **后续阶段：** 通过新增技能扩展到 build/repair 场景，且保持插件标识 `simulink-automation-suite` 不变。

![路线图](docs/assets/readme/roadmap.png)
