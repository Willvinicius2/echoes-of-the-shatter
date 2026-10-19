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
