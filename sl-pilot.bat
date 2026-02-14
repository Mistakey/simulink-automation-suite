@echo off
REM ========================================================
REM  Simulink Pilot Launcher
REM  Automatically activates 'sl_ai' conda env and runs core
REM ========================================================

REM 1. 激活 Conda 环境 (请修改为你电脑上实际的 activate.bat 路径)
REM    通常在 C:\Users\你的用户名\anaconda3\Scripts\activate.bat
call C:\Users\33137\anaconda3\Scripts\activate.bat sl_ai

REM 2. 运行同目录下的 Python 核心脚本
REM    %~dp0 代表当前 .bat 文件所在的目录
REM    %* 代表把你在命令行输入的所有参数原样传给 Python
python "%~dp0sl_core.py" %*

REM 3. (可选) 运行完如果不需要保持环境，脚本结束自动回到原环境