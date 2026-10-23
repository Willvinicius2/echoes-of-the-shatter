cd /d/openclaude/_trabalho-claude; export TEMP=D:/openclaude/_trabalho-claude/tmp TMP=D:/openclaude/_trabalho-claude/tmp
B="/c/Program Files/Blender Foundation/Blender 5.1/blender.exe"; S=wt/arqueiro-dark-3d/art-src/modelos/scripts; PY=/d/openclaude/_ferramentas/TripoSG/.venv/Scripts/python.exe; W=D:/openclaude/_trabalho-claude/modelos3d/arqueiro_dark/arco/work4
# ordem completa: geo (3300) -> bake -> blade -> paint -> export -> prancha. Rodar parcial: bash run_arco4.sh blade|paint ...
case "$1" in
full) timeout 900 $PY $S/arco_v4_geo.py 3300 | tail -3; timeout 1200 "$B" -b -P $S/arco_v4_bake.py 2>&1 | grep -E "TRIS|Error";;
esac
timeout 300 $PY $S/arco_v4_blade.py $BLADE_ARGS | tail -3
timeout 600 $PY $S/arco_v4_paint.py | tail -1
timeout 300 "$B" -b -P $S/arco_v4_export.py -- $W/bow_v4.glb 2>&1 | grep -E "FOLGA|EMPUN|BBOX|TRIS|OK|Error|Trace"
timeout 300 "$B" -b -P $S/arco_v4_prancha.py -- $W/bow_v4.glb $W/r 2>&1 | grep -E "Error|Trace"
