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
