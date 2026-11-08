# 34 — Fases jogáveis, desbloqueio e elite do portão

Fluxo que permite ter mais de uma fase no cliente 2D (Ato I: Cripta dos Ecos e Pedreira dos Ecos). O mapa da Pedreira (`godot/data2d/rooms/fase_2.txt`) vem de outro processo; enquanto ele não existe, a Pedreira aparece no título como "em breve".

## Regra de destrancar
- A Cripta (`cripta`) começa aberta. A Pedreira (`pedreira`) abre depois da primeira vitória na Cripta (passar pelo portal depois do chefe).
- Fase trancada: cartão com cadeado e a dica "Vença a Cripta dos Ecos para abrir". Fase aberta sem o arquivo da sala: "Em breve". Nos dois casos o botão Jogar fica desativado.
- Na primeira vitória que abre uma fase nova, a tela de fim mostra uma vez "Pedreira dos Ecos desbloqueada!".
- A fase escolhida fica gravada e volta na próxima sessão.

## Tabelas
- `godot/data2d/fases_2d.csv` (cliente): `id, sala, onda_fase, nome, descricao, requer`. `nome` e `descricao` são chaves de `loc_fase.csv`; `onda_fase` é o id da fase em `ondas_fases.csv`; `requer` é o id da fase que precisa ser vencida (vazio = aberta).
- `ondas_fases.csv`, `ondas.csv` e `curva_horda.csv` (core): a Pedreira tem 7 ondas em 420 s (a Cripta tem 8 em 480 s). O começo é um pouco mais duro que na Cripta (orçamento 100 contra 80 e curva de vida 0,32 contra 0,25 na onda 1), e o fim tem o mesmo teto (orçamento 520, teto 40, curva 1,0/0,85 na última onda e 1,1/0,95 no enxame). Os elites usam `elite_vida` 4 e `elite_dano` 1,5. A assinatura da fase são as matilhas de `ash_hound` (peso 4 em todas as ondas) e o `stone_herald` (da onda 2 em diante, peso 1 a 3). O portão desperta a partir da onda 4.
- Save: o save do meta (`user://save_2d.json`) é escrito pelo core, então as fases ficam num arquivo ao lado, `user://save_2d_fases.json`: `{"versao": 1, "fases_vencidas": [...], "fase_escolhida": "..."}`. Save antigo, sem esse arquivo, abre sem nenhuma fase vencida e na Cripta.

## Elite do portão
O chefe da Pedreira é o `ossuary_captain`, um inimigo `melee` comum de `enemies.csv`. Ele não aparece nas ondas comuns da Pedreira. O core o trata como chefe da fase: ele nasce marcado como `boss`, com a vida adaptativa (`boss_fight_time`, `boss_hp_min`, `boss_hp_max`), e o portal abre quando ele morre. O cliente, quando o chefe não é `kind=boss`, faz dele o elite do portão (decisão do Jev):
- usa a IA comum (não o script do Guardião), espera no ponto `G` do mapa e acorda quando o jogador chega perto, como o Guardião;
- escala `gate_elite_scale` (1,5) no sprite e no raio de colisão, sem o tom dourado nem a escala 1,2 dos elites de onda; conta como elite para XP, baú e gema;
- entrada de `gate_elite_intro` (1,4 s): fica parado e invulnerável, com um clarão de luz aditivo no portão, um tremor leve de tela e o aviso com o nome dele;
- barra de vida grande no topo da tela, com o nome por chave de localização (`enemy.ossuary_captain.name`). Ela some quando ele morre.
A Cripta não muda: o Guardião continua com o script e a barra dele.

## Como testar
- Suíte: `godot --headless --path godot --script res://scripts2d/tools/test_2d.gd` (os testes de fases ficam em `scripts2d/tools/test_fases_2d.gd`; a corrida da Pedreira usa `data2d/testes/fases_teste.csv`, que aponta a Pedreira para a sala de `fase_1.txt`).
- Abrir todas as fases sem vencer: comando `fases_abertas` no console (`), `dev_fases_abertas,1` em `run_settings.csv` (só build de debug) ou `-- --fases-abertas`. `-- --fase=pedreira` escolhe a fase pela linha de comando.
- Capturas: `scripts2d/tools/captura_fases_2d.gd -- <prefixo>` (título, tela de fim e o elite do portão).

## Pontos para o design decidir
- Vida do elite do portão: a regra adaptativa limita a vida a `boss_hp_max` (2,5) vezes a vida base. Para o capitão (240) isso dá no máximo 600, contra até 3.250 do Guardião. Com o DPS do fim da corrida ele pode morrer em poucos segundos. Ajustar exige uma vida própria do capitão como chefe, ou limites por fase no core.
- O capitão como chefe não recebe a curva de dano da onda (o core só aplica a curva a comuns e elites). Ele bate com o dano base de `enemies.csv` (20).
