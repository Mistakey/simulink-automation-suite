# Simulink Automation Suite — Backlog

发现来源：日常使用、FOC 模型搭建实践（2026-03）、live test、用户反馈、代码审查。
每条目包含优先级、类别、发现场景、具体描述。

**优先级定义**
- `P0` 关键缺失，严重阻塞工作流
- `P1` 高频痛点，显著降低效率
- `P2` 改善体验，较重要
- `P3` 锦上添花

**管理规则**
- 已修复的条目直接从 backlog 中删除（修复记录在 git 历史中，不在此文件保留）。
- 经审查合并或移除的条目保留在"已关闭 / 合并条目"表中，防止重复提出。

---

## 缺失功能（Missing Features）

### F-003 `line_add` 支持 LConn/RConn 物理电气端口 `P0`
**场景**：SPS（SimPowerSystems）所有电气连接使用 `LConn1`、`RConn1` 等物理端口名称。
**问题**：`line_add` 仅支持整数端口号，直流母线、逆变器、PMSM 之间的电气连接全部无法通过 CLI 完成。
**建议**：端口字段支持字符串名称：
```json
{"action": "line_add", "model": "m", "src": "DC_Source/RConn1", "dst": "Ground1/LConn1"}
```

---

### F-005 `block_copy` action `P2`
**场景**：工程中需要复用参考模型中已配好参数的子系统。
**问题**：缺少从已有模型复制模块的 action。`block_add` 只能从库添加（默认参数），无法复制已配置的模块。
**建议接口**：
```json
{"action": "block_copy", "src": "RefModel/PID_Subsystem", "dst": "MyModel/PID_Subsystem"}
```

> **注**：原描述以 `powergui` 为例（"无法从 SPS 库直接添加，只能复制"）有误——`powergui` 可通过 `block_add` 从 `powerlib/powergui` 正常添加，当时失败的原因是库未加载和不知道正确路径。`block_copy` 的真正场景是复制已配参数的子系统，但使用频率不高，且 F-001 实现后可通过 `run_matlab("add_block('src','dst')")` 替代，优先级由 P1 降为 P2。

---

### F-006 `set_param` 原子多参数更新 `P1`
**场景**：Repeating Sequence 的 `rep_seq_t` 和 `rep_seq_y` 必须同时更新；任何参数组合有依赖关系时均会触发此问题。
**问题**：CLI 每次只设一个参数，分步设置触发中间态校验报错（如 `Length of time vector and output vector must be the same`）。
**建议**：`set_param` 支持 `params` 对象，一次提交多个 key-value：
```json
{"action": "set_param", "target": "m/PWM_Carrier", "params": {"rep_seq_t": "[0 5e-5 1e-4]", "rep_seq_y": "[-1 1 -1]"}}
```

---

### F-007b `log_signals` 零配置信号捕获 `P3`
需要诊断中间信号时，必须手动添加/删除 ToWorkspace 块，流程繁琐。建议 `simulate` 支持：
```json
{"action": "simulate", "log_signals": ["MyModel/Speed_PI/1", "MyModel/Park_Iq/1"]}
```
仿真时自动注入临时 ToWorkspace 块，结束后自动清理。

> 实现复杂度高（总线信号、虚拟子系统边界、信号名冲突等边界情况多），且可通过 F-001（`run_matlab`）脚本方式达到相同效果，优先级降为 P3。

---

## Bug / 行为问题（Bugs）

### B-001 SPS 物理连接无法通过 `connections` 追踪 `P2`
**问题**：`connections` 只追踪 Simulink 信号线，无法追踪 SPS LConn/RConn 物理电气连接，电气拓扑完全不可见。
**建议**：扩展 `connections` 支持物理连接，或新增 `electrical_connections` action。

---

## 改进 / 优化（Improvements）

### I-003 `model_update` 返回完整诊断信息 `P1`
**场景**：模型存在警告或非致命错误时，当前 `model_update` 只返回 pass/fail。
**建议**：返回完整 warning/error 列表，包含块路径、错误代码、描述文本，便于 AI 自动定位并修复问题：
```json
{"warnings": [{"block": "BasicFOC/Iq_PI", "code": "SL_UNCONNECTED_INPUT", "message": "Input port 2 is unconnected"}]}
```

---

## 已关闭 / 合并条目（Closed / Merged）

> 以下条目经审查后合并到其他条目或判定为不需要，保留记录以避免重复提出。

| 原编号 | 标题 | 处置 | 说明 |
|--------|------|------|------|
| F-002 | `workspace_read/write` | 合并入 F-001 | `evalin`/`assignin` 通过 `run_matlab` 实现 |
| F-007a | `simulate` 返回仿真输出 | 合并入 F-001 | 仿真结果通过 `run_matlab` 读取 workspace 变量获得 |
| F-008 | `sim_results` 动态指标分析 | 移除 | 超调量、调节时间等指标 AI 从原始数据自行计算，不应嵌入 CLI |
| F-009 | `get_bus_signals` | 转为 I-004 | 已可通过 `inspect --param InputSignals` 实现，问题在 skill 文档未教会 AI |
| F-010 | `get_port_info` | 部分转为 I-004，其余由 F-001 覆盖 | 基础端口信息可通过 `inspect` 获取；完整查询需 `run_matlab` |
| F-011 | MATLAB Function 块源码读取 | 合并入 F-001 | 需 Stateflow API（`sfroot` → `EMChart` → `Script`），非 `get_param` 可达 |
| F-012 | Data Dictionary 访问 | 合并入 F-001 | 通过 `Simulink.data.dictionary.open` API 实现 |
| I-001(旧) | SPS 常用模块路径文档 | 移除 | 特定工具箱的库路径应运行时发现（F-001 / MATLAB MCP），非静态维护 |
| I-002(旧) | `inspect` 增加 `resolve_value` | 合并入 F-001 | 表达式求值通过 `run_matlab` 实现 |
| I-004(旧) | `set_param` 增加 `force_update` | 移除 | `set_param` + `model_update` 两步调用等价，增加 API 复杂度无实际价值 |
| I-005(旧) | skill 补充 SPS 限制说明 | 拆分 | SPS 文档部分移除（同 I-001 旧理由）；通用使用模式部分保留为新 I-004 |
| B-001(旧) | `block_add` source 路径含换行符 | 降级为 I-002 | 代码已正确支持（`allow_control_chars=True`），仅为文档/提示改进 |
| B-002(旧) | 标准库模块需要预先加载 | 降级为 I-001 | 非 bug，是 MATLAB 预期行为；改为 CLI 增强（自动 load_system） |

---

## SPS 模型搭建实践总结（通用经验）

> 来源：2026-03 FOC 模型搭建过程，与具体模型无关，下次搭建仍有效。

### 需要绕道 MATLAB engine 的操作（因上述缺失功能导致）
| 操作 | 根本原因 | 对应条目 |
|---|---|---|
| SPS 电气连接（LConn/RConn） | CLI 不支持物理端口名称 | F-003 |
| 多参数原子更新（如 PWM 载波） | 分步设置触发中间态校验报错 | F-006 |

### SPS 常用模块信息（经验积累）
| 信息 | 内容 |
|---|---|
| PMSM 总线信号顺序 | `[ias, ibs, ics, iqs, ids, vqs, vds, ha, hb, hc, w, theta, Te]`（13 路）|
| PMSM theta 含义 | 机械角（rad），需乘以极对数得电气角 |
| PMSM RefAngle 默认 | `90 degrees behind phase A`，Park 变换角需补偿 -π/2 |
| Universal Bridge 门极 | 6 路信号 `[G1..G6]`，上下桥臂交替排列，需 DataTypeConversion 转 double |
