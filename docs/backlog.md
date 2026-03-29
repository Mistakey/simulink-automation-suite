# Simulink Automation Suite — Backlog

发现来源：日常使用、FOC 模型搭建实践（2026-03）、live test、用户反馈、代码审查。

**优先级定义**
- `P0` 关键缺失，严重阻塞工作流
- `P1` 高频痛点，显著降低效率
- `P2` 改善体验，较重要
- `P3` 锦上添花

---

## 待处理

（暂无）

---

## 已解决（v2.9.0, 2026-03-29）

FOC 模型搭建实践发现的全部问题已在 `fix/backlog-quick-wins` 分支解决：

- FEAT-001 `model_copy` action
- FEAT-002 `simulate` timeout + 仿真结果存 workspace（`sl_sim_result`）
- FEAT-003 `block_add` 跨模型复制
- FEAT-004 `sim-analyst` subagent（替代原始 `get_logged_signal` 方案）
- FEAT-005 `block_add` / `line_add` 批量模式
- PAIN-001 `--json-file` CLI 选项
- PAIN-002 `matlab_eval` 换行文档
- DOC-001/002/003 SKILL.md 文档补充
- IMPROVE-001 UTF-8 输出（`ensure_ascii=False`）
- IMPROVE-002 `source_not_found` 路径建议（`difflib`）
- FEAT-006 已确认非缺陷，关闭

---

### FOC_Basic 模型最终状态（2026-03-29）

- **文件**：`FOC_Basic.slx`（仓库根目录）
- **基础**：从 Foc_BaseVer 复制，保留 SPS 功率级（PMSM + Universal Bridge IGBT + DC 电源 + powergui 离散模式）
- **简化内容**：Observer=0（直接使用真实角度 eTheta_real，跳过观测器估算）；负载转矩=0（空载测试）
- **速度指令**：Constant2=500 rpm（原值 12000 rpm 导致 PI 振荡，已调整到可稳定工作的测试点）
- **仿真验证结果**（StopTime=1.0s，Ts=5e-7s，Tsample=1e-4s）：
  - t=0.05s: 455 rpm（上升中）
  - t=0.10s: 524 rpm（约5%超调）
  - t=0.50s: 505 rpm（接近稳定）
  - t=1.00s: **500.6 rpm**（稳态误差 0.1%）✓
- **编译状态**：零诊断错误，仅有 SPS 库预存 `display` 方法名警告（非本次引入）
