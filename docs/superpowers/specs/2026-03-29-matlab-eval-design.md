# F-001 `matlab_eval` — 任意 MATLAB 代码执行

**日期**：2026-03-29
**状态**：设计完成，待实现
**对应 Backlog**：F-001（P0）

## 动机

当前 CLI 的每个 action 只能完成一种预定义操作。没有执行任意 MATLAB 代码的途径，导致以下能力全部缺失：

- workspace 读写（`evalin` / `assignin`）
- 仿真结果读取
- 参数表达式求值
- Bus Selector 信号查询
- 端口信息查询
- MATLAB Function 块源码读取（Stateflow API）
- Data Dictionary 访问
- 库路径发现

`matlab_eval` 作为单一通用入口解锁以上全部能力，与 MathWorks 官方 MATLAB MCP Core Server 的 `evaluate_matlab_code` 设计方向一致。

## 设计决策

| 决策 | 结论 | 理由 |
|------|------|------|
| 安全层级 | Operational + 软护栏 | 任意代码不可 dry_run/rollback；软护栏防 agent 失误（代码过长、输出爆炸、死循环） |
| 一个还是两个 action | 一个 `matlab_eval` | 底层相同，YAGNI |
| 命名 | `matlab_eval` | 对齐 `noun_verb` 模式（`block_add`、`model_open`）；`eval` 是 MATLAB 原生术语 |
| 输出捕获 | `evalc` 纯文本 | 最简单可预测；MathWorks MCP 同样只返回文本；agent 天然能解析 |

## 接口定义

### 请求字段（FIELDS）

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `code` | string | 是 | — | 要执行的 MATLAB 代码，支持多行 |
| `timeout` | number | 否 | 30 | 执行超时（秒），防死循环/超长仿真 |
| `session` | string | 否 | null | MATLAB session 名称，走现有 session 解析逻辑 |

### 成功响应

```json
{
  "action": "matlab_eval",
  "output": "ans =\n    2.6704\n",
  "truncated": false,
  "warnings": []
}
```

### 输出截断

`output` 超过 **50,000 字符** 时截断尾部：

```json
{
  "action": "matlab_eval",
  "output": "...(截断后的文本)...",
  "truncated": true,
  "total_length": 128000,
  "warnings": []
}
```

50,000 字符约覆盖 99% 正常用例，防止大矩阵 `disp` 撑爆 context window。

### 错误码

| 错误码 | 场景 |
|--------|------|
| `engine_unavailable` | MATLAB Engine 不可用（复用） |
| `no_session` | 无可用 session（复用） |
| `session_not_found` | 指定 session 不存在（复用） |
| `session_required` | 多 session 未指定（复用） |
| `eval_failed` | MATLAB 代码执行报错，message 含 MATLAB error |
| `eval_timeout` | 执行超时 |
| `runtime_error` | 非预期异常（复用） |

## 实现结构

### Transport 层

`matlab_transport.py` 新增：

```python
def eval_code(engine, code, timeout=30):
```

- 调用 `engine.evalc(code, nargout=1)` 捕获文本输出
- 超时通过 Python MATLAB Engine 的 `async` + `result(timeout=...)` 机制实现（引擎原生支持）
- 超时抛异常，由 action 层捕获转为 `eval_timeout`
- 复用 `_reset_lastwarn()` / `_drain_warnings()` 捕获 warnings

### Action 模块

`simulink_cli/actions/matlab_eval.py`：

```
DESCRIPTION / FIELDS / ERRORS  — 标准 exports
validate(args)                 — code 非空、timeout 正数、session 合法
execute(args)                  — safe_connect_to_session → eval_code → 截断 → 构造响应
```

遵循现有 action module contract，无新模式。

### 注册

`core.py`：

```python
from .actions import matlab_eval as matlab_eval_cmd
_ACTIONS["matlab_eval"] = matlab_eval_cmd
```

## 测试策略

### 1. Schema 合规（自动覆盖）

`test_schema_action.py` 已有框架，注册后自动验证 FIELDS/ERRORS/DESCRIPTION exports。

### 2. 输入验证（`test_matlab_eval.py`）

- `code` 为空 → `invalid_input`
- `code` 非 string → 类型错误
- `timeout` 为负数/零 → 报错
- `timeout` 非 number → 类型错误
- 未知字段 → `unknown_parameter`

### 3. 执行测试（mock engine）

- 正常执行 → 返回 output + warnings
- MATLAB 报错 → `eval_failed` + 错误信息
- 超时 → `eval_timeout`
- 输出超 50,000 字符 → `truncated: true` + `total_length`
- session 解析（复用现有 session mock 模式）

### 4. Docs contract（自动覆盖）

`test_docs_contract.py` 已有框架，新 action 注册后自动检查文档同步。

### 5. Live 验证

Unit test 不能替代实机。Transport 层的 `evalc` + async timeout 行为需通过 `/live-test` 在真实 MATLAB 上验证。
