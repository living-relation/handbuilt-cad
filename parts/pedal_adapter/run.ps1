.venv\Scripts\python.exe pedal_adapter.py
.venv\Scripts\python.exe check.py $args[0]
.venv\Scripts\python.exe rmodel.py
Compress-Archive -Force C:\Users\danie\agent-tools\pedal-parametric\work_m_*.png, "C:\Users\danie\agent-tools\pedal-parametric\work_$($args[0])_*.png" C:\Users\danie\agent-tools\pedal-parametric\work_m.zip
"PIPELINE DONE"
