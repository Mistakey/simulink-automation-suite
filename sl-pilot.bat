@echo off
REM ========================================================
REM  Simulink Pilot Launcher (Fixed)
REM ========================================================

REM [Help Mode] Prints the README for AI context
IF "%1"=="help" (
    echo.
    echo [INFO] Loading documentation...
    echo ---------------------------------------------------
    type "%~dp0README.md"
    echo.
    echo ---------------------------------------------------
    EXIT /B 0
)

REM [Execution Mode] Activates environment and runs python
REM Note: Adjust the path below to your actual activate.bat location
call C:\Users\33137\anaconda3\Scripts\activate.bat sl_ai
python "%~dp0sl_core.py" %*