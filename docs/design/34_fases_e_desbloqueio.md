# 34 — Fases jogáveis, desbloqueio e elite do portão

Fluxo que permite ter mais de uma fase no cliente 2D (Ato I: Cripta dos Ecos e Pedreira dos Ecos). O mapa da Pedreira (`godot/data2d/rooms/fase_2.txt`, gerado por `tools/mapas/gerar_fase_2.py`; visão geral, arte e capturas em `docs/arte/35_pedreira_dos_ecos.md`) já existe, então a Pedreira abre pelo título depois da primeira vitória na Cripta; o cartão "em breve" só aparece se o arquivo da sala sumir.

## Regra de destrancar
- A Cripta (`cripta`) começa aberta. A Pedreira (`pedreira`) abre depois da primeira vitória na Cripta (passar pelo portal depois do chefe).
- Fase trancada: cartão com cadeado e a dica "Vença a Cripta dos Ecos para abrir". Fase aberta sem o arquivo da sala: "Em breve". Nos dois casos o botão Jogar fica desativado.
- Na primeira vitória que abre uma fase nova, a tela de fim mostra uma vez "Pedreira dos Ecos desbloqueada!".
- A fase escolhida fica gravada e volta na próxima sessão.

## Tabelas
- `godot/data2d/fases_2d.csv` (cliente): `id, sala, onda_fase, nome, descricao, requer`. `nome` e `descricao` são chaves de `loc_fase.csv`; `onda_fase` é o id da fase em `ondas_fases.csv`; `requer` é o id da fase que precisa ser vencida (vazio = aberta).
- `ondas_fases.csv`, `ondas.csv` e `curva_horda.csv` (core): a Pedreira tem 7 ondas em 420 s (a Cripta tem 8 em 480 s). O começo é um pouco mais duro que na Cripta (orçamento 100 contra 80 e curva de vida 0,32 contra 0,25 na onda 1), e o fim tem o mesmo teto (orçamento 520, teto 40, curva 1,0/0,85 na última onda e 1,1/0,95 no enxame). Os elites usam `elite_vida` 4 e `elite_dano` 1,5. As ondas só usam inimigos que já têm folha de sprite e stats: `skeleton_soldier`, `hollow_sentinel`, `crypt_bat`, `wandering_ghost`, `ghost_archer` e `chain_wraith` (o teste `test_pedreira_2d.gd` falha com qualquer outro). A assinatura pensada para a fase, as matilhas de `ash_hound` e o `stone_herald`, está **pendente de arte (PixelLab sem saldo)**: quando as folhas existirem, voltam às ondas (`ash_hound` em todas e `stone_herald` da onda 2 em diante, como no desenho original). O portão desperta a partir da onda 4.
- **Regra de arte para toda fase** (direção de arte): nenhuma fase vai ao jogador com a caixa provisória. O teste `test_fases_2d.gd` (`_testar_arte_das_fases`) percorre a tabela `fases_2d.csv` e falha se uma onda (`ondas.csv`), o chefe ou o enxame (`ondas_fases.csv`) ou um `@guarda` do mapa da fase usar um inimigo sem stats em `enemies.csv`, sem as 5 animações no manifesto (idle, run, attack, hit e death), com folha ausente, com menos de 5 direções ou com o PNG de tamanho diferente do manifesto (`scripts2d/tools/arte_inimigos_2d.gd`). Uma fase nova entra na tabela já coberta por esse teste. A Cripta usa substitutos até as folhas do Cão de Cinza, do Arauto de Pedra e do Carcereiro existirem (ver `docs/arte/35_pedreira_dos_ecos.md`).
- Save: o save do meta (`user://save_2d.json`) é escrito pelo core, então as fases ficam num arquivo ao lado, `user://save_2d_fases.json`: `{"versao": 1, "fases_vencidas": [...], "fase_escolhida": "..."}`. Save antigo, sem esse arquivo, abre sem nenhuma fase vencida e na Cripta.

## Elite do portão
O chefe da Pedreira é o `ossuary_captain`, um inimigo `melee` comum de `enemies.csv`. Ele não aparece nas ondas comuns da Pedreira. O core o trata como chefe da fase: ele nasce marcado como `boss`, com a vida adaptativa (`boss_fight_time`, `boss_hp_min`, `boss_hp_max`), e o portal abre quando ele morre. O cliente, quando o chefe não é `kind=boss`, faz dele o elite do portão (decisão do Jev):
- usa a IA comum (não o script do Guardião), espera no ponto `G` do mapa e acorda quando o jogador chega perto, como o Guardião;
- escala `gate_elite_scale` (1,5) no sprite e no raio de colisão, sem o tom dourado nem a escala 1,2 dos elites de onda; conta como elite para XP, baú e gema;
- entrada de `gate_elite_intro` (1,4 s): fica parado e invulnerável, com um clarão de luz aditivo no portão, um tremor leve de tela e o aviso com o nome dele;
- luz própria: um halo aditivo laranja preso a ele, atrás do sprite (`gate_elite_luz_tamanho` e `gate_elite_luz_alfa` em `run_settings.csv`, pulsa de 70% a 100%), além do poço de luz do mapa nos pés dele (`@luz` de 3 tiles sobre o G); acendem o chão e recortam o elite, sem pintar o osso de laranja; aparece na captura do portão;
- barra de vida grande no topo da tela (`chefe_elite_y` em `hud_layout.csv`, 20 px abaixo da barra do Guardião), com o nome numa placa escura e por chave de localização (`enemy.ossuary_captain.name`). Ela some quando ele morre.
O portão onde ele espera é o `pedreira_portao` (portal de pedra maciça com grade de ferro e guindaste, não o arco da área 1); só se chega ao portal (X) pelo vão dele. A Cripta não muda: o Guardião continua com o script e a barra dele.

## Como testar
- Suíte: `godot --headless --path godot --script res://scripts2d/tools/test_2d.gd` (os testes de fases ficam em `scripts2d/tools/test_fases_2d.gd` e os do mapa, do portão, da orla de terra e das ondas da Pedreira em `scripts2d/tools/test_pedreira_2d.gd`; a corrida da Pedreira usa `data2d/testes/fases_teste.csv`, que aponta a Pedreira para a sala de `fase_1.txt`).
- Abrir todas as fases sem vencer: comando `fases_abertas` no console (`), `dev_fases_abertas,1` em `run_settings.csv` (só build de debug) ou `-- --fases-abertas`. `-- --fase=pedreira` escolhe a fase pela linha de comando.
- Capturas: `scripts2d/tools/captura_fases_2d.gd -- <prefixo>` (título, tela de fim e o elite do portão).

## Pontos para o design decidir
- Vida do elite do portão: a regra adaptativa limita a vida a `boss_hp_max` (2,5) vezes a vida base. Para o capitão (240) isso dá no máximo 600, contra até 3.250 do Guardião. Com o DPS do fim da corrida ele pode morrer em poucos segundos. Ajustar exige uma vida própria do capitão como chefe, ou limites por fase no core.
- O capitão como chefe não recebe a curva de dano da onda (o core só aplica a curva a comuns e elites). Ele bate com o dano base de `enemies.csv` (20).
