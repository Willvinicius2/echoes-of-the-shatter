#!/usr/bin/env bash
# Gera a build jogável do cliente 2D (GDScript, sem C#).
# Uso: tools/build/build_2d.sh [saida] [godot]   (Godot 4.4.x com export templates instalados)
set -euo pipefail
raiz="$(cd "$(dirname "$0")/../.." && pwd)"
saida="${1:-$raiz/build}"
godot="${2:-godot}"
proj="$(mktemp -d)"
for d in scripts2d scenes2d art2d; do ln -s "$raiz/godot/$d" "$proj/$d"; done
# data2d é copiado: o Godot importaria os CSV como tradução e o export perderia o arquivo cru.
# O importador "keep" mantém os CSV como estão (o cliente os lê com FileAccess).
cp -r "$raiz/godot/data2d" "$proj/data2d"
# O mesmo vale para os WAV, lidos em bytes por audio_2d.gd (a cópia de art2d também sai do symlink).
rm "$proj/art2d"; cp -r "$raiz/godot/art2d" "$proj/art2d"
find "$proj/data2d" "$proj/art2d/audio" \( -name '*.csv' -o -name '*.wav' \) | while read -r f; do
  printf '[remap]\n\nimporter="keep"\n' > "$f.import"
done
python3 - "$raiz" "$proj" <<'PY'
import re, sys
raiz, proj = sys.argv[1:3]
s = open(raiz + '/godot/project.godot').read()
s = s.replace('"4.7", "C#", "Forward Plus"', '"4.4", "Forward Plus"')
s = re.sub(r'\[dotnet\]\n\nproject/assembly_name="[^"]*"\n\n', '', s)
open(proj + '/project.godot', 'w').write(s)
PY
cp "$raiz/tools/build/export_presets_2d.cfg" "$proj/export_presets.cfg"
mkdir -p "$saida/windows" "$saida/linux"
"$godot" --headless --path "$proj" --import >/dev/null 2>&1 || true
"$godot" --headless --path "$proj" --export-release Windows "$saida/windows/EcosDosEstilhacos.exe"
"$godot" --headless --path "$proj" --export-release Linux "$saida/linux/EcosDosEstilhacos.x86_64"
rm -rf "$proj"
