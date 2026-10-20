# Projeto Godot (.NET) — Echoes of the Shatter

Godot 4.7.2 estável .NET e SDK .NET 8 ficam em `D:\Godot` (`editor\`, `dotnet\`). O MCP do Godot (Coding-Solo/godot-mcp, código aberto) está em `D:\Godot\mcp\godot-mcp`.

## Abrir a Cripta
```
D:\Godot\editor\Godot_v4.7.2-stable_mono_win64\Godot_v4.7.2-stable_mono_win64.exe --path D:\openclaude\echoes-godot\godot
```
A cena principal é `scenes/cripta/Cripta.tscn`. Câmera de estudo: WASD move, Q/E gira, roda do mouse dá zoom.

## Reconstruir a cena e as capturas (modo texto)
Variáveis de ambiente: `DOTNET_ROOT=D:\Godot\dotnet`, `NUGET_PACKAGES=D:\Godot\nuget`, `DOTNET_CLI_HOME=D:\Godot\dotnet-home`.
```
dotnet build EchoesOfTheShatter.csproj
Godot_console.exe --headless --path . --import
Godot_console.exe --headless --path . --script res://scripts/tools/build_cripta.gd
Godot_console.exe --path . --script res://scripts/tools/captura.gd -- saida.png alvoX alvoZ distancia yaw pitch
```
`build_cripta.gd` monta pisos, paredes, braseiros, pilares e clima a partir do layout em `docs/tecnico/14_layout_cripta.md`.

## Módulos 3D
Gerados no Blender por `art-src/cenario/modulos/modulos_cripta.py` (um `.glb` por módulo em `art/models/`). Os materiais `M_Pedra` e `M_PedraEscura` são trocados pela pedra triplanar via remap no `.glb.import` (criados por `scripts/tools/make_materiais.gd`).
