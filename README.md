# Simulink Automation Suite (AI Context)

这是一套用于控制本地 MATLAB/Simulink 的 CLI 工具。

## ⚠️ 关键指令 (Critical Instructions)

1. **环境**: 不需要手动激活 Conda。直接运行 `sl-pilot` 命令即可，它会自动处理环境。
2. **命令**:
   - `sl-pilot scan` : 获取当前模型的拓扑结构（JSON 格式）。
   - `sl-pilot highlight --target "路径"` : 高亮指定模块。
3. **约束**:
   - 必须确保本地 MATLAB 已经打开并运行了 `matlab.engine.shareEngine`。
   - 如果遇到 Python 报错，请检查 `sl_core.py`。