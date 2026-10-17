.venv\Scripts\python.exe pedal_adapter.py
.venv\Scripts\python.exe check.py $args[0]
.venv\Scripts\python.exe rmodel.py
Compress-Archive -Force $env:USERPROFILE\agent-tools\pedal-parametric\work_m_*.png, "$env:USERPROFILE\agent-tools\pedal-parametric\work_$($args[0])_*.png" $env:USERPROFILE\agent-tools\pedal-parametric\work_m.zip
"PIPELINE DONE"
