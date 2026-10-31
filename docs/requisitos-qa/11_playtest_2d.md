# 11 — QA automático e roteiro de playtest (cliente 2D)

Setor C do roadmap (`docs/design/27_cronograma_jogavel.md`, seção 11). Cobre o cliente 2D top-down de `godot/scripts2d/`.

## 1. O que roda sozinho a cada PR (workflow `cliente2d.yml`)
| Job | O que faz | Quando falha |
|---|---|---|
| `teste-headless` | `test_2d.gd`: manifesto, salas, upgrades, chefe, corrida completa, rotas, meta, forja | alguma linha `FALHA` ou `SCRIPT ERROR` |
| `corridas-bot` | `corridas_2d.gd`: 10 corridas completas com um bot sem god mode (mira no mais próximo, mantém distância, esquiva, escolhe cartas e rotas ao acaso) | alguma corrida trava (mais de 240 s simulados numa sala ou 1500 s na corrida) ou o Godot reporta erro de script |
| `export` | `tools/build/build_2d.sh`: gera `EcosDosEstilhacos.exe` (Windows) e `.x86_64` (Linux) | export falha ou arquivo não existe |

O job `corridas-bot` sobe o artefato `metricas-corridas` (JSON + Markdown) e escreve a tabela no resumo do job. O job `export` sobe `build-windows` e `build-linux`.

### Rodar o bot localmente
```
godot --headless --fixed-fps 600 --path godot --script res://scripts2d/tools/corridas_2d.gd -- 10 saida 1
```
`--fixed-fps 600` deixa a simulação ~10x mais rápida que o tempo real (uma corrida leva ~10 s em vez de ~100 s). Argumentos depois de `--`: número de corridas (10), pasta de saída (`.`), semente do bot (1). Mortes não reprovam o PR; elas viram métrica. Só travar reprova.

### Como ler o relatório
- **Mortes por sala** alta numa sala (por exemplo mais de 40% das entradas) indica pico de dificuldade: vai para o setor B (balanceamento).
- **Tempo médio por sala** muito acima das vizinhas indica sala longa ou inimigo difícil de acertar.
- **Vitórias = 0 de 10** com o bot não é bug: o bot é fraco de propósito. Compare entre PRs, não com um número absoluto.
- O bot usa semente fixa; a mesma semente reproduz as escolhas de cartas e rotas.

## 2. Roteiro de playtest manual (20 min, na build do artefato)
Anote em cada passo: passou (P), falhou (F) ou estranho (E), com uma linha de descrição.

### 2.1 Primeiros 5 minutos
1. Abrir o jogo: título aparece, música toca, botões respondem ao mouse e ao teclado.
2. Jogar: sala 1, WASD move, mouse mira, clique atira, Espaço esquiva. O personagem responde sem atraso perceptível.
3. Matar todos: porta abre, aparece a escolha de 3 cartas, escolher uma e atravessar a porta.
4. Pausa com Esc e retomar. Reiniciar com R depois de morrer.

### 2.2 Corrida completa
5. Chegar a uma bifurcação de rota e testar os dois caminhos em corridas diferentes (combate, elite, descanso).
6. Chegar ao chefe: entrada, fases, transição e vitória. Conferir tempo e fragmentos na tela final.
7. Morrer de propósito em salas diferentes: o resumo mostra sala, tempo e ganhos.
8. Gastar fragmentos na Forja e começar nova corrida: o efeito vale na corrida seguinte.

### 2.3 Sensação (game feel)
9. Hit stop, tremor e números de dano estão legíveis, sem enjoar em 5 minutos de luta.
10. O telégrafo dos ataques dá tempo de reagir (esquiva cabe na janela).
11. Câmera, HUD e barra do chefe sem cortes em 1280x720, 1920x1080 e tela cheia.

### 2.4 Estabilidade
12. 10 corridas seguidas sem travar, sem queda de FPS visível e sem erro no console.
13. Fechar e abrir: o progresso (fragmentos, Forja) persiste.
14. Linux e Windows: mesma sequência nas duas builds.

### 2.5 Relato
Para cada falha: build (data/commit), plataforma, passo do roteiro, o que esperava, o que aconteceu, captura de tela. Abrir como issue com a etiqueta `playtest`.

## 3. Critério de saída para o Acesso Antecipado (QA)
- `teste-headless` verde em `master`.
- `corridas-bot` com 0 travadas em 3 execuções seguidas com sementes diferentes.
- Nenhuma sala com mais de 60% de mortes do bot sem decisão registrada do setor B.
- Roteiro 2.1 a 2.4 completo nas duas plataformas, sem item F.
