# 21 — Roteiro da Região 1: Cripta Partida (rascunho)

Base: pitch de história do Will (18/10/2026): Generais, veredito Exorcizar/Devorar, Fome e Ecos da Queda. **Substitui, para a narrativa, a seção 3 do `00_plano_existente.md`** (Aural, Vespéria e o Arquivo Vivo), o que precisa do "de acordo" do dono. Falas provisórias em `Content/Data/Loc/dialogue.csv` (chaves `dlg.*`, `ui.verdict.*`). Não há tabela de quests no repositório; as missões abaixo são proposta de design, sem CSV.

## Premissa
Sob a Cinza, o Caçador (forasteiro que a Cinza não prende) devolve o mundo região a região. Cada Região = Rastrear, Cercar, Duelo, Veredito (+ salto de anos). Região 1: **Cripta Partida**, General **o Guardião**.

## Cenas
1. **Refúgio, chegada** — Ilsa explica o Caçador e a Cinza (`dlg.ilsa.intro_1..3`). Tico reage (`dlg.tico.intro`).
2. **Rastrear** — trecho antes da Cripta: Anomalias comuns e Ecos da Queda (armas quebradas, memórias). Os Ecos mostram o martelo em cone e o escudo frontal do Guardião. Tico guarda os Ecos (`dlg.tico.echo_found`); Ilsa dá a pista (`dlg.ilsa.general_lore`).
3. **Cercar** — a Cripta já na build: Sentinelas, elites, desafios de ambiente.
4. **Duelo** — Guardião em 2 fases; na 2ª invoca 2 Sentinelas (`dlg.guardian.phase1`, `phase2`).
5. **Veredito** — ele cai de joelhos (`dlg.guardian.kneel`), tela com aviso de escolha irreversível (`ui.verdict.*`).
   - *Exorcizar*: últimas palavras e um fragmento a mais (`dlg.guardian.last_words`), Relíquia do Descanso, região purificada, Refúgio vira vila fortificada.
   - *Devorar*: golpe-assinatura do Guardião, +atributos, Fome 1, Mancha na região (elites e loot exclusivo), Refúgio com guarnição.
6. **Salto de anos** — o Refúgio muda; NPCs envelhecem (`dlg.ilsa.after_*`, `dlg.ilsa.years_pass`, `dlg.tico.after_years`).

## Missões (proposta)
| ID sugerido | Nome | Objetivo | Quem dá | Recompensa |
|---|---|---|---|---|
| `quest.r1.first_call` | O chamado | Falar com Ilsa e ir à Cripta | Ilsa | Marco de Retorno liberado |
| `quest.r1.echoes` | Cacos da Queda | Achar os Ecos da Cripta (quantidade a definir) | Tico | Fraqueza do Guardião revelada |
| `quest.r1.siege` | Cerco | Chegar à câmara do Guardião | Ilsa | Acesso ao duelo |
| `quest.r1.verdict` | Veredito | Derrubar o Guardião e escolher | — | Exorcizar ou Devorar |

## Para decidir (dono)
- Aprovar a troca de narrativa (Aural/Vespéria → Generais) e o destino de Bram e Odete (hoje só nomes sem função).
- Criar tabela de quests e de Ecos (esquema em `docs/tecnico/06_dados.md`) antes de ligar isso ao jogo.
- Chaves de Fome, Mancha e finais ficam para depois.

## Complemento (18/10): NPCs do Refúgio e Região 2
Narrativa aprovada pelo dono em 18/10 (Generais e veredito no lugar da seção 3 do plano).

### Bram, o Ferreiro e Irmã Odete, a Leitora
- **Bram**: perdeu a memória do ofício, mas as mãos lembram. Reforja as armas quebradas dos Ecos (ideia do pitch); reage à Fome (`dlg.bram.*`).
- **Odete**: ex-aprendiz de Vespéria no plano antigo; agora lê os Ecos e avisa sobre o veredito, sem dizer toda a verdade (`dlg.odete.*`). Vespéria sai da narrativa.
- Funções de jogo (forja, Livros, árvore) seguem as decisões de `15_etapas.md`; nada ligado ao cliente ainda.

### Região 2: Planícies Cinzentas (A Arqueira)
- **Rastrear**: campo aberto, Anomalias comuns, Ecos de flechas partidas.
- **Cercar**: torres e elites de longo alcance, sem cobertura.
- **Duelo**: à distância, forçando fechar espaço; falas `dlg.archer.*`.
- **Reconstrução**: Exorcizar vira vila com plantações; Devorar vira posto avançado.
- Cada General luta com o estilo do herói que foi (Ecos mostram os golpes antes).

### Regiões 3 e 4 e a Fenda
- **Cidade Submersa (O Sábio)**: Rastrear em ruas alagadas, Ecos de livros molhados; Cercar com zonas de perigo; Duelo de áreas e ilusões (`dlg.sage.*`). Reconstrução: distrito de porto.
- **Bosque das Almas (A Curandeira)**: Ecos de ervas e almas presas; duelo que drena vida e invoca almas (`dlg.healer.*`). Reconstrução: santuário e hospitais.
- **Fenda de Colisão (O Líder)**: duelo com a lâmina quebrada; ele conta a verdade e oferece a última escolha (`dlg.leader.*`). O final (Descanso, Herança ou Cisma) vem do total de vereditos (`ui.ending.*`). Texto completo em `22_pitch_historia.md`.

## Dados da Região 1 (18/10)
Tabelas em `EchoesOfTheShatter/Content/Data/Story/` (`regions`, `echoes`, `quests`, `verdicts`) e textos em `Loc/story.csv`. Ficam em subpasta de propósito: o core ainda não as lê (ele recusa CSV desconhecido na raiz). Validação: `python3 tools/dados/validate_story.py`. Valores de Fome e bônus (`hungerDelta`, `statBonusPct`) são provisórios. O próximo passo é o core carregar as tabelas e guardar a escolha, a Fome e os Ecos no save (save v3), decisão de contrato a revisar com Opus.

### Core da história (18/10)
`ShatterCore/include/shatter/story.h` carrega `Story/` (`StoryDB`) e aplica as regras: `RecordEcho`, `IsSkillRevealed`, `ApplyVerdict` (exige o General vencido, é irreversível, soma a Fome até `hunger_max` de `Story/story_rules.csv`) e `TotalStatBonusPct`. O estado vai no campo opcional `story` do save v2 (como `world_state`): saves sem história mantêm os mesmos bytes e hash, então não houve salto para save v3 nem migração. Falta expor tudo na API C (`shatter_c.h`) para o cliente Unity, contrato novo a revisar.

### Cliente Unity da história (19/10)
Código em `UI/StoryDirector.cs` (nasce sozinho nas cenas Cripta e Refúgio quando há save e a pasta `Story/`), `UI/VerdictScreen.cs`, `UI/EchoPickup.cs` e `Interop/Native/SaveGame.Story.cs` / `StoryDb`. Tudo que é regra continua no core.
- **Ecos**: 3 brilhos provisórios na Cripta (r01, r05 e r07, um por linha de `echoes.csv`), recolhidos com Interagir (`shatter_story_record_echo`, grava o save, avisa e confirma o golpe revelado).
- **Veredito**: depois de vencer o Guardião (o `RunRecorder` já registrou a morte no save), mostra a fala `dlg.guardian.kneel` e abre a tela com Exorcizar e Devorar, aviso de escolha irreversível e botão de segurar 1 s. O jogo pausa enquanto a tela está aberta.
- **Fome**: marcador "Fome ●●○○" no canto da HUD, só depois do primeiro veredito.
- **Bônus**: `stat_bonus_pct` do core vira modificador "aumentado" em Vida, Dano e Armadura do herói (`SaveGame.StoryStatBonusPct`). O simulador idle também lê o bônus: o pedido da expedição guarda `story_stat_bonus_pct` (campo opcional, ver abaixo).
- **Refúgio**: faixa com `hub.*.name` e `hub.*.desc` e um tom leve na luz ambiente (verde para vila, laranja para guarnição). Os modelos de cada estado exigem arte nova e passam pela aprovação do dono.

Decisões tomadas sem o Will (ele dormia): bônus em Vida, Dano e Armadura; Fome só aparece depois do primeiro veredito; pontos dos Ecos nas salas r01, r05 e r07.

### Efeitos do veredito no jogo (19/10, core)
Decisões sem o Will (ele dormia), todas com número em `Story/story_rules.csv` e `skills.csv`:
- **Relíquia do Descanso**: cura de poção +25% (`relic_potion_effect_pct`), modificador "aumentado" em `PotionEffect`. A resistência à Cinza do pitch fica para quando a Cinza tiver mecânica.
- **Golpe devorado**: `skill.devoured.guardian_slam` em `skills.csv` (cone físico de área, coeficientes provisórios 1,6/1,8/2,0, recarga 8 s, sem classe). IDs sem classe agora também aceitam `skill.devoured.*` no validador e no core. Ligado à barra do herói (19/10, ver "Golpe devorado na barra" abaixo).
- **Mancha**: nas áreas de uma região com veredito Devorar, a chance de elite de cada grupo sobe 15 pontos (`stain_elite_bonus_pct`) na expedição idle. No combate manual a Mancha também entra (ver abaixo).
- **Idle**: `ExpeditionRequest` ganhou `storyStatBonusPct`, `storyPotionEffectPct` e `storyEliteBonusPct` (JSON `story_*`, 0..100, só gravados se > 0; saves antigos mantêm os mesmos bytes). O cliente calcula os valores a partir de `shatter_story_state_json` (`potion_effect_pct`, `stain_elite_bonus_by_map`) e os envia nos parâmetros de início. C# não compilado nesta sessão.

### Golpe devorado na barra, Fome e Mancha no combate manual (19/10, core + C# não compilado)
Decisões sem o Will (ele dormia), números em `Story/story_rules.csv`, `loot_*.csv`:
- **Golpe na barra**: com o veredito Devorar, `skill.devoured.guardian_slam` entra no último espaço livre da barra do herói (F; `DevouredKit.FillBar`). Vale para qualquer classe.
- **Custo em Fome**: cada uso gasta `devoured_hunger_cost` (1) de Fome *da corrida*, ou seja, a Fome do save (que só sobe pelo veredito) mais os usos desde que o herói entrou ou renasceu. Passou de `hunger_max` (4), o golpe é negado com o aviso "Fome no limite" (`DenyReason.Hunger`). A conta da corrida fica no C# (`DevouredKit`) por ser protótipo; o número vem do core e a regra deve migrar para o core numa etapa futura (ressalva da revisão Opus). A Fome do save não muda com o uso, para não punir para sempre. "Perder o controle" com a Fome cheia do pitch fica para depois.
- **Mancha no manual**: `shatter_encounter_roll_json_ex` soma `stain_elite_bonus_pct` (15) à chance de elite de cada grupo da Cripta quando a região foi Devorada. O `EncounterDirector` lê o valor direto do core no `Awake`.
- **Loot exclusivo**: encontro limpo numa área com Mancha rola também `loot.crypt.stain` (25% de chance, só mágico e raro, conjunto do Guardião e escudo). Provisório: o exclusivo é a raridade e o escudo; um Único da Mancha fica para o design.

Pendências abertas: aparência real do Refúgio por estado; ver a passagem de bastão `atoI-faltas-20261019.md` para o que falta no Ato I.

### Falas da Região 1 ligadas ao cliente (19/10, C# não compilado)
Decisões sem o Will (ele dormia), sem tocar core nem save:
- **Quem fala o quê**: `UI/StoryLines.cs` escolhe as chaves de `dialogue.csv` pelo estado da história (Ecos e veredito) que o core já expõe. Ilsa: `intro_1..3` até o primeiro Eco, `general_lore` com Ecos, `after_exorcise|devour` + `years_pass` depois do veredito. Tico: `intro`, `echo_found`, `after_years`. Bram: `intro`, `echo_blade`, `after_devour`, `farewell`. Odete: `intro`, `echo_read`, `warning` (só antes do veredito), `farewell`. As falas aparecem no topo do cartão de conversa; a expedição de Ilsa e Tico segue embaixo.
- **Sem marca de "já ouvi"** (substituído pelas missões, ver abaixo): não havia campo no save para isso, então a introdução se repete a cada conversa até achar o primeiro Eco. Se incomodar, a marca vira campo do core numa etapa futura.
- **Bram e Odete**: o `StoryDirector` cria duas cápsulas com rótulo no Refúgio (-8,0 e -12,0), sem mexer na cena montada; só falas, a forja e os Livros seguem sem função. Modelos exigem arte aprovada.
- **Guardião**: `dlg.guardian.phase1` ao começar a luta e `phase2` quando ele invoca as Sentinelas (aviso em faixa); `kneel` e `last_words` já existiam no veredito.
- **Salto de anos**: sem arte nem gatilho próprio; por ora `years_pass` e `after_years` são falas dos NPCs depois do veredito. Mesmas falas nos dois caminhos, trocando só `after_exorcise`/`after_devour`.
- **Missões**: ligadas depois pela thread de Missões (ver seção abaixo), inclusive `dlg.ilsa.crypt_done`.

### Missões da Região 1 no jogo (19/10, core testado + C# não compilado)
Decisões tomadas sem perguntar (Will dormia); o número e os textos estão em `Story/quests.csv` e `Loc/story.csv`.
- **Progresso é regra do core**, não só texto: `story.quests` no save (campo opcional dentro de `story`; saves sem missões mantêm os mesmos bytes). Cada missão guarda `progress` e `done` (permanente).
- **Cadeia**: uma missão só avança depois da que ela `requires`. `collect_echo` e `verdict` avançam sozinhos (`RecordEcho`, `ApplyVerdict`); Ecos achados antes de a missão liberar contam depois. `talk` e `reach_map_boss` o cliente avisa (`shatter_story_quest_event`).
- **Recompensa** (`unlock.return_marker`, `reveal.general_weakness`, `unlock.duel`) é só uma chave: o cliente mostra o aviso ("Recompensa: ..."). Nenhum efeito mecânico novo: o Marco de Retorno e o duelo seguem sem bloqueio, e a fraqueza do Guardião já vem dos Ecos (`IsSkillRevealed`). Travar o Marco ou o duelo por missão fica para quem decidir esse design.
- **Diário (tecla J)**: `QuestJournal` lista as missões liberadas e as concluídas, com progresso; trancadas não aparecem. Conclusão avisa em faixa. Pausa e inventário não abrem com o diário aberto.
- **Gatilhos no cliente**: `talk` ao conversar com qualquer NPC do Refúgio (`AddStoryLines`), `reach_map_boss` quando o Guardião entra em luta (`ArenaPhase.Fighting`). `StoryDirector.ReportQuest(type, target)` é o ponto de entrada para outros gatilhos.
- **Marca de "introdução já ouvida"**: usa `quest.r1.first_call` (falar com a Ilsa). Primeira conversa mostra `intro_1..3`; as seguintes, `general_lore`. `dlg.ilsa.crypt_done` abre a fala da Ilsa depois do veredito (`quest.r1.verdict` concluída).
- Arquivos: `StoryDirector.Quests.cs`, `QuestJournal.cs` (novos), `StoryLines.cs`, `RefugeController.cs`, `StoryTypes.cs`, `SaveGame.Story.cs`. Testes: `story_quests_*`, `c_api_story_quests_*` (core) e `Quests_FromCore_*`, `StoryLines_IntroPlaysOnce*` (EditMode, não rodados).
