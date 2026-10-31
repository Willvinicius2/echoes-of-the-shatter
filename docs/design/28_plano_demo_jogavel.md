# 28. Plano da demo jogável (31/10/2026)

O Will pediu uma demonstração jogável para ver como está a base. Este plano define o escopo, o que já está no `master`, o que falta e como o Will recebe o build. Decisões tomadas pelo Jev (`jev-latest`, `POST /v1/systemone`); confiança abaixo de 0,5 é provisória.

## 1. Decisões do Jev
| Pergunta | Decisão | Probabilidades | Conf. |
|---|---|---|---|
| Escopo da demo | Corrida completa da Região 1 com hub, Forja e meta-progressão, usando só o que está no `master` | a 88%, b (com PRs 110/112/117) 11%, c (sem hub) 1% | 0,82 |
| Como o Will recebe o build | Rodar do código no Godot do PC (opção c, 76%). Como o CI já exporta Windows/Linux, o artefato `build-windows` fica como caminho alternativo, sem custo extra | a 14%, b 10%, c 76% | 0,64 |
| Guardião antes da demo | Suavizar primeiro (menos vida/dano nos CSV) e conferir com o bot | a 52%, b 48% | 0,04 (provisória) |

Como a confiança da terceira é baixa, a suavização é leve e reversível (só números em CSV), e o Will diz no teste se ainda está difícil ou fácil.

## 2. Escopo da demo
- **Dentro**: título/hub (fragmentos, materiais, amuleto), Forja com receitas, Melhorias de meta, corrida de 4 etapas da Região 1 com rotas (combate, elite e descanso), cartas de upgrade, Guardião da Cripta, game over e vitória, opções, tutorial da primeira corrida, áudio CC0 atual, save em disco.
- **Fora**: Região 2, MMO/co-op, Steam real (GodotSteam fica atrás de interface), áudio final (setor E), migração ao ShatterCore (pacote 2 do M10).
- **Visual**: o do `master` (ícones provisórios geométricos e HUD atual). Os PRs 110 (HUD v4), 112 (combate lapidado) e 117 (ícones) esperam o sim do Will e **não** entram na demo; quando forem mesclados, uma segunda rodada de demo os inclui.

## 3. O que já está no `master`
Conteúdo da Região 1 (PR 118), opções, tutorial e interface Steam (119), textos da loja (120), bot de QA com 10 corridas automáticas, relatório de métricas e export Windows/Linux no CI (121), além de hub com Forja (M8), exploração por rotas (M9), meta com save (M7) e o módulo `rogue` do core (M10 pacote 1, ainda não ligado ao cliente).

## 4. O que falta antes de entregar
| Item | Dono | Entrega |
|---|---|---|
| Suavizar o Guardião | setor B (`boss_patterns_2d.csv`, `enemies.csv`) | **Feito**: vida 1500→1300 e dano 20→18 em `enemies.csv`; mortes do bot na sala do chefe caíram de 67% (6 entradas, 2 vitórias) para 50–57% em duas sementes |
| Conferir CI do `master` | setor C | `test_2d.gd`, `corridas-bot` e `export` verdes no último commit; artefatos `build-windows` e `build-linux` presentes |
| Roteiro de teste | setor C | `docs/requisitos-qa/11_playtest_2d.md` já serve; adicionar ao fim uma lista de 10 perguntas que o Will responde depois de jogar |
| Salas por etapa, variação de chefe, teto de cartas acima de 8 | setor B / A | **Não bloqueiam a demo**; entram depois do feedback |

## 5. Como o Will joga
1. **Pelo código**: abrir `godot/` no Godot 4.4.1 (D:\openclaude), cena principal `scenes2d/Run2D.tscn`, F5. Controles: WASD move, mouse mira, clique atira, Espaço esquiva, R reinicia ao morrer (`godot/COMO_RODAR_2D.md`).
2. **Pelo build do CI** (alternativo): em GitHub Actions, workflow `cliente2d`, último run no `master`, artefato `build-windows`; descompactar e abrir `EcosDosEstilhacos.exe`. O save fica no perfil do usuário e não precisa de instalação.
3. **O que testar**: uma corrida completa até o Guardião; morrer de propósito uma vez e voltar ao hub; criar um amuleto na Forja; comprar uma melhoria; escolher uma rota de elite e uma de descanso.

## 6. Critério de pronto da demo
- CI verde no `master` com os dois artefatos de build.
- Uma corrida completa chega ao Guardião e termina (vitória ou morte) sem erro de script nem travamento; o bot confirma em 10 corridas.
- Hub, Forja e meta funcionam entre corridas e o save persiste ao fechar e reabrir.
- O Will recebe, no chat principal, os dois caminhos (código e artefato) e as 10 perguntas de feedback.

## 7. Depois do feedback
O Jev decide a prioridade com base nas respostas: fechar PRs 110/112/117, setor B (salas por etapa, variação de chefe, teto de cartas) ou M10 pacote 2.
