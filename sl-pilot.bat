@echo off
REM ========================================================
REM  Simulink Pilot Launcher (Fixed)
REM ========================================================

REM [Help Mode] Prints AI-focused usage context
IF "%1"=="help" (
    echo.
    echo [INFO] Loading help context...
    echo ---------------------------------------------------
    if exist "%~dp0AI_HELP.md" (
        type "%~dp0AI_HELP.md"
    ) else (
        type "%~dp0README.md"
    )
    echo.
    echo ---------------------------------------------------
    EXIT /B 0
)

REM [Execution Mode] Activates environment and runs python
REM Note: Adjust the path below to your actual activate.bat location
call C:\Users\33137\anaconda3\Scripts\activate.bat sl_ai
python "%~dp0sl_core.py" %*
