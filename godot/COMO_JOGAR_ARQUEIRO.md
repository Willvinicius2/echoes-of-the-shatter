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
`Godot_console.exe --path godot [--resolution 1280x720] -- --arqueiro-teste` roda a sequência, imprime linhas `TESTE:` e grava PNGs em `capturas_arqueiro/`. As ações de entrada vêm de `scripts/tools/make_input.gd`. O teste injeta eventos reais (`Input.ParseInputEvent`): mouse (movimento e botão), analógico direito, analógico esquerdo, gatilho direito e botão B.

O que ele prova:
- Mira por mouse: pixel -> ponto no plano do chão (altura `tiro_altura`) confere com um cálculo independente (câmera pinhole) com erro 0,000 m em 1000x700, 1280x720, 1600x900 e 1920x1080; a flecha sai na direção da mira (erro 0,0 graus) e acerta um boneco colocado ali. Com a câmera em movimento e o mouse parado na tela, o ponto de mira acompanha o chão (erro máximo ~0,07 m, um quadro de atraso da câmera).
- Analógico direito (direção = eixos da câmera), esquerdo (anda para a frente da câmera), gatilho (carrega e solta) e B (esquiva).
- Flecha cravada: `06_flecha_parede.png`, `06b` (recorte ampliado) e `06c` (recorte em ~3,5 s) mostram a flecha presa numa parede; some depois de `flecha_cravada_tempo` (4 s). Corrida: `02_andando.png` e `02b_andando.png`.

## Mudanças recentes
- Correr: velocidade máxima 3,8 m/s (era 4,5). Walk até 40% disso (1,5 m/s). O clipe Run toca a 0,7x–1,6x (`anim_escala_min_correr`, `anim_escala_max_correr`); o Walk, até 2,6x.
- A flecha sai no evento `solta` do clipe Release (quadro 2 de 9, ~0,06 s depois de soltar o botão), não mais no instante do clique. Esquivar antes disso dispara a flecha na hora.
- Os i-frames da esquiva seguem os eventos `iframes_inicio` e `iframes_fim` do clipe Dodge (quadros 2 e 12 de 14, esticados ao `esq_tempo`). A troca para a pose de corda cheia usa `corda_cheia` do Draw. Quadros e durações dos clipes estão em `arqueiro.csv` (`evt_*`), copiados de `art-src/animacao/arqueiro_eventos.json`; se o clipe mudar, atualize ali.
- Haste da flecha mais grossa e com leve brilho, para ler no escuro.
- Aviso: os pilares da Cripta não têm colisão; a flecha os atravessa (assunto do cenário).
