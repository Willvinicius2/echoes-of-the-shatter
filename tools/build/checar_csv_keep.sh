#!/usr/bin/env bash
# Confere que todo CSV de dados do cliente 2D tem importador "keep".
# Sem isso o Godot 4.4 importa o CSV como tradução (csv_translation): cada coluna vira um Translation
# criado numa thread de importação, e Translation::set_locale põe na fila da thread principal uma
# chamada para esse objeto, que já foi liberado quando a fila roda. O --import cai às vezes com
# "double free or corruption" ou signal 11. O cliente lê os CSV com FileAccess, não como Translation.
# Para corrigir um CSV novo:  printf '[remap]\n\nimporter="keep"\n' > godot/data2d/<arquivo>.csv.import
set -euo pipefail
raiz="$(cd "$(dirname "$0")/../.." && pwd)"
falhou=0
while IFS= read -r f; do
  if ! grep -qx 'importer="keep"' "$f.import" 2>/dev/null; then
    echo "FALHA: ${f#$raiz/} precisa de $(basename "$f").import com importer=\"keep\""
    falhou=1
  fi
done < <(find "$raiz/godot/data2d" -name '*.csv')
exit $falhou
