**语言：** [English](README.md) | **简体中文**

# Simulink Automation Suite

![Claude Code Plugin](https://img.shields.io/badge/Claude_Code-Plugin-4A5568)
![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![MATLAB](https://img.shields.io/badge/MATLAB-Engine-orange)

Simulink Automation Suite 是一个基于 MATLAB Engine for Python 的 Claude Code 插件，用于 Simulink 只读自动化分析流程。

- 插件标准名称：`simulink-automation-suite`
- 当前已发布技能：`simulink-scan`
- 运行时 Python 模块路径：`skills.simulink_scan`（仅模块命名使用）

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
2. 技能先解析 MATLAB 会话上下文（`session list/use/current/clear`），并使用精确会话名匹配。
3. 然后执行核心动作之一：`schema`、`list_opened`、`scan`、`connections`、`inspect`、`find`、`highlight`。
4. 结果通过 `stdout` 输出为机器可读 JSON。
5. 异常通过稳定错误码返回，便于 Agent 做恢复重试。

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
| `schema` | 返回机器可读的命令契约 | `python -m skills.simulink_scan schema` |
| `list_opened` | 列出当前已打开的 Simulink 模型 | `python -m skills.simulink_scan list_opened` |
| `scan` | 读取模型/子系统拓扑结构 | `python -m skills.simulink_scan scan --model "my_model" --recursive` |
| `connections` | 读取目标模块的上游/下游关键连接模块 | `python -m skills.simulink_scan connections --target "my_model/Gain" --direction both --depth 1 --detail summary` |
| `inspect` | 读取模块参数和有效值 | `python -m skills.simulink_scan inspect --model "my_model" --target "my_model/Gain" --param "All"` |
| `highlight` | 在 Simulink 中高亮目标模块（仅 UI 定位，不修改模型） | `python -m skills.simulink_scan highlight --target "my_model/Gain"` |
| `find` | 按名称模式和/或模块类型搜索模块 | `python -m skills.simulink_scan find --model "my_model" --name "PID"` |
| `session` | 管理当前 MATLAB 共享会话 | `python -m skills.simulink_scan session list` |

---

## 输出控制

当需要更紧凑的返回结果时，可使用截断与字段投影参数：

```bash
python -m skills.simulink_scan scan --model "my_model" --max-blocks 200 --fields "name,type"
python -m skills.simulink_scan inspect --model "my_model" --target "my_model/Gain" --param "All" --max-params 50 --fields "target,values"
python -m skills.simulink_scan connections --target "my_model/Gain" --detail ports --max-edges 50 --fields "target,edges,total_edges,truncated"
python -m skills.simulink_scan find --model "my_model" --name "PID" --max-results 50 --fields "path,type"
```

---

## JSON 请求模式

`--json` 是一等入口，且与基于参数的动作调用互斥。
`schema` 返回结构化字段元数据（类型、必填/默认值/枚举、字段说明）。

```bash
python -m skills.simulink_scan --json "{\"action\":\"schema\"}"
python -m skills.simulink_scan --json "{\"action\":\"list_opened\",\"session\":\"MATLAB_12345\"}"
python -m skills.simulink_scan --json "{\"action\":\"scan\",\"model\":\"my_model\",\"recursive\":true,\"session\":\"MATLAB_12345\"}"
python -m skills.simulink_scan --json '{"action":"connections","target":"my_model/Gain","direction":"both","depth":1,"detail":"summary","max_edges":50,"fields":["target","upstream_blocks","downstream_blocks"]}'
python -m skills.simulink_scan --json '{"action":"find","model":"my_model","name":"PID","max_results":50,"fields":["path","type"]}'
```

---

## 严格默认行为与错误契约

- 会话匹配仅支持精确匹配（不支持模糊匹配）。
- 当 MATLAB 共享会话多于一个时，涉及 MATLAB 连接的动作必须显式传 `--session`。
- JSON 中出现未知字段会返回 `unknown_parameter`。
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
- `no_session`
- `session_required`
- `session_not_found`
- `model_required`
- `model_not_found`
- `subsystem_not_found`
- `invalid_subsystem_type`
- `block_not_found`
- `inactive_parameter`
- `runtime_error`

如果没有可用 MATLAB 共享会话，请先在 MATLAB 中执行 `matlab.engine.shareEngine` 再重试。

---

## 仓库内容

```text
simulink-automation-suite/
|-- .claude-plugin/
|   |-- plugin.json
|   |-- marketplace.json
|-- skills/
|   |-- simulink_scan/
|       |-- SKILL.md
|       |-- reference.md
|       |-- test-scenarios.md
|       |-- scripts/
|-- tests/
|-- docs/
|-- README.md
|-- README.zh-CN.md
```

---

## 验证

```bash
python -m unittest discover -s tests -p "test_*.py" -v
claude plugin validate .
```

---

## 路线图

- **当前阶段（v1.2.x）：** 完成只读分析基础能力，包括 `schema`、`session`、`list_opened`、`scan`、`connections`、`inspect`、`highlight`，并强化面向 Agent 的严格契约。
- **下一阶段：** 在保持可预测契约与恢复链路的前提下，增强 Agent 工作流编排与可靠性。
- **后续阶段：** 通过新增技能扩展到 edit/build/repair 场景，且保持插件标识 `simulink-automation-suite` 不变。

![路线图](docs/assets/readme/roadmap.png)
