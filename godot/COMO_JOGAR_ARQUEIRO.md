# Arqueiro jogável na Cripta

## Abrir
```
D:\Godot\editor\Godot_v4.7.2-stable_mono_win64\Godot_v4.7.2-stable_mono_win64.exe --path D:\openclaude\_trabalho-claude\wt\arqueiro\godot
```
Na primeira vez: `dotnet build EchoesOfTheShatter.csproj` (variáveis DOTNET_ROOT, NUGET_PACKAGES, DOTNET_CLI_HOME em `D:\Godot`, ver `COMO_RODAR.md`). A cena principal é `scenes/cripta/CriptaJogavel.tscn`.

## Controles
| Ação | Teclado e mouse | Controle |
|---|---|---|
| Mover | WASD ou setas | analógico esquerdo |
| Mirar | mouse (plano do chão) | analógico direito |
| Atirar | segurar botão esquerdo (carga) e soltar | RT ou R1 |
| Esquivar | Espaço | B |
| Alternar câmera (arqueiro / estudo) | C | |
| Dano de teste (animações Hit e Death) | H | |
| Renascer | R | |

## O que testar
- Andar e correr (Walk/Run por velocidade), giro suave, rampas e escadas da Cripta.
- Esquiva: impulso curto, poeira, recarga, i-frames.
- Tiro: carga curta dá flecha fraca e curta; carga total (0,8 s) dá flecha rápida, forte e de longo alcance. Acerte os 3 bonecos de treino (vida, flash, número de dano, hit stop leve, tremor de câmera). Flecha na parede fica cravada alguns segundos.
- H até a vida zerar: Hit e Death; renasce sozinho ou com R.
- Números em `data/arqueiro/arqueiro.csv`; equipamento por ID em `data/arqueiro/equipamento.csv` e `loadout.csv`; textos em `data/loc/arqueiro.csv`.

## Teste automático
`Godot_console.exe --path godot -- --arqueiro-teste` roda a sequência (andar, esquiva, tiro no boneco, tiro na parede, dano, morte), imprime linhas `TESTE:` e grava PNGs em `capturas_arqueiro/`. As ações de entrada vêm de `scripts/tools/make_input.gd`.
