# Passagem de bastão: Guerreiro jogável no nível do Arqueiro

Atualizado em 11/11/2026, ao fechar a thread "Levar o Guerreiro ao nível jogável". Contexto enxuto: a linha "Guerreiro" de `godot/COMO_RODAR_2D.md`, `godot/data2d/habilidades_guerreiro.csv` e `godot/data2d/afinidades_guerreiro.csv`.

## Feito
- **Mesma partida do Arqueiro.** O Guerreiro usa as cartas de nível do core (`upgrades_2d.gd`); o `corrida_guerreiro_2d.gd` (cartas próprias, só ao limpar a sala) saiu. `guerreiro.csv` passou a usar os nomes de stat das cartas (`arrow_damage` = dano da espada, `shoot_cooldown` = intervalo do combo, `arrow_count` = Lâmina Dupla, `arrow_pierce` = Lâmina Longa, `crit_chance`, `run_*`).
- **Golpe básico com elemento.** A primeira gema abre "Escolha o Eco da sua lâmina": trovão (o 3º golpe salta em arco para vizinhos), peste (arco mais largo, envenena), gelo (acumula frio e congela no 4º) e cinzas (+10% de dano, queima e o 3º golpe deixa brasa). Números em `afinidades_guerreiro.csv`; leitura comum em `afinidades_2d.gd` (`defs`, `ids`, `elemento`, por classe).
- **Habilidades.** Além das 12 ativas de aço que já existiam, 8 ativas de elemento com mecânica própria (Golpe do Trovão, Lâminas da Tempestade, Onda Flamejante, Erupção, Cravar Gélido, Escudo de Geada, Talho Pestilento, Estandarte da Peste) e os 4 Arautos. Código em `efeitos_guerreiro_2d.gd`.
- **Arte sem serviço pago.** Folhas do herói em pixel art no formato do Arqueiro (92 px, pivô 46,76, escala 2,5) por `tools/sprites2d/pixelar_heroi.py`; 15 folhas de efeito por `tools/arte/fx_guerreiro/gerar.py` (catálogo em `godot/art2d/fx/guerreiro/catalogo.json`, tocadas por `fx_guerreiro_2d.gd`); 12 ícones por `tools/arte/icones_por_codigo/glifos_guerreiro.py`.
- **Textos.** `loc_guerreiro.csv` traz nomes e descrições e a variante `.guerreiro` das cartas comuns (`Csv.t_classe`), usada também na dica do tutorial.
- **Testes.** `test_guerreiro_2d.gd` cobre dados, árvore, combate, as 20 ativas, Ecos, cartas e a horda. O bot `partida_2d.gd` aceita `--classe=guerreiro` e luta de perto.
- Capturas, pranchas e o vídeo da partida: `/mnt/project-files/capturas/guerreiro/`.

## Falta
1. **Ícones das cartas comuns** (Disparo Múltiplo, Alcance Amplo e outras) ainda mostram flechas para o Guerreiro; só o texto muda. Pede ícone por classe (`icone_<id>_guerreiro.png`) e um `Icones.textura_classe`.
2. **Balanceamento.** Na partida do bot o Guerreiro quase não perde vida nas primeiras ondas. Os números das habilidades novas são um primeiro chute; revisar junto com a rodada de XP e ondas.
3. **Fundo do título** mostra sempre o Arqueiro, qualquer que seja a classe escolhida.
4. **Cores dos ramos de aço** (`ramo_lamina`, `ramo_baluarte`, `ramo_impeto`) não existem em `tema.csv`; as cartas caem na cor de destaque.
5. **Regras no ShatterCore.** Os efeitos das ativas e dos Ecos do Guerreiro ainda são GDScript, como os do Arqueiro; migram juntos.

## Atenção
- A thread do Mago cria o mesmo `afinidades_2d.gd` e mexe no mesmo trecho de afinidade de `run_2d.gd` e `upgrade_ui_2d.gd`. O contrato combinado é `defs(classe)`, `ids(classe)`, `elemento(id)` lendo `data2d/afinidades_<classe>.csv`. Quem mesclar depois adapta no rebase.
- CSV novo em `data2d/` precisa do `.import` com `importer="keep"` (`tools/build/checar_csv_keep.sh`).
- Depois de `godot --import`, desfaça os `.import` rastreados que o editor mexeu: `git ls-files -m | grep '\.import$' | xargs -r git checkout --`.
