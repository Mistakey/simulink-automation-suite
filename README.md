# Simulink Automation Suite (AI Context)

This is a CLI toolkit for interacting with a local running MATLAB/Simulink session via Python Engine.

## [CRITICAL] Instructions for AI Agent

1. Environment:
   - Just run the 'sl-pilot' command directly.

2. Commands:
   - 'sl-pilot scan'
     > Returns topology JSON.
   
   - 'sl-pilot highlight --target "BlockPath"'
     > Highlights a block.

   - 'sl-pilot scan --session MATLAB_12345'
     > Connects to a specific shared session if multiple MATLABs are open.

3. Troubleshooting (Read carefully):
   - **"No shared MATLAB session found"**: 
     If you see this error, you MUST ask the user to run `matlab.engine.shareEngine` in their MATLAB Command Window. DO NOT try to fix it yourself.