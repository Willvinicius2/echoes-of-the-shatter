# 02 — Requisitos e critérios de aceite (Vision Lead)

Projeto: **Echoes of the Shatter** · Rodada: "base do jogo" · Data: 15/10/2026
Fonte de verdade de design: `docs/design/00_plano_existente.md` (Plano Steam v2.0). Plano da equipe: `docs/requisitos-qa/01_plano_execucao.md`.
Mudança decidida pelo dono: motor **Unreal Engine 5** (substitui Godot 4). Onde isso altera o plano, ver seção 6.

Legenda de verificação usada em todo o documento:
- **[SC]** verificável por teste automático no **ShatterCore** (C++17 puro, CMake, roda no Linux deste workspace).
- **[UE]** exige o **editor UE5** ou um build do jogo; verificação manual pelo dono do projeto.
- **[SC+UE]** a regra é testada no ShatterCore e a apresentação/integração é conferida no UE5.

---

## 1. Visão do produto

Echoes of the Shatter é um ARPG single-player em 3D estilizado pintado à mão, com câmera fixa em 3/4, vendido na Steam por preço fechado (Acesso Antecipado, PC Windows, offline, sem conta e sem servidor), no qual o jogador conquista cada área e cada chefe jogando na mão e depois manda o personagem farmar essas rotas sozinho enquanto o jogo está fechado. O idle é complemento, nunca substituto: ele rende a taxa base, nunca abre conteúdo e nunca entrega os itens de topo; jogar na mão ativa o Fervor do Recuperador. Pitch: *"Conquiste na mão. Domine a rota. Deixe seu herói farmar enquanto você vive."*

### Os 4 pilares

| Pilar | Na prática | Teste de que funciona |
|---|---|---|
| Conquistar pela ação | Toda área e todo chefe novo exigem jogar na mão; o idle nunca abre conteúdo | Jogadores preferem jogar a próxima área a só coletar expedições |
| Build com identidade | Livros ensinam habilidades, Sigilos modificam, itens mudam o jeito de jogar | Três builds da mesma classe se jogam de forma visivelmente diferente |
| Planejar o retorno | A expedição é um quebra-cabeça: rota, regras de IA, poções, duração | O relatório gera uma decisão (trocar item, ajustar regra) |
| Respeitar o tempo | Sessão de 5 min já rende progresso; sessão longa rende conquista | Quem joga 15 min/dia continua progredindo e voltando |

Nesta rodada, o protótipo precisa provar o primeiro e o terceiro pilar no menor recorte possível: **lutar na Cripta é gostoso** e **a expedição da Cripta gera uma decisão**.

---

## 2. Escopo do protótipo desta rodada ("base do jogo")

Corte vertical mínimo, menor que o demo do Next Fest (que tem Estrada + Cripta e 4 habilidades). Tudo o que está aqui deve ser dirigido por dados (`Content/Data/*.csv`) e todas as regras numéricas passam pelo ShatterCore.

### 2.1 Dentro do escopo

| Item | Conteúdo do protótipo | Observação |
|---|---|---|
| Classe | **Guerreiro**, recurso **Ímpeto** | Sem especialização; nível máximo do protótipo **6** |
| Hub | **Refúgio do Marco**: Ilsa (expedições) e Tico (relatório e entrega do loot) | Bram e Irmã Odete aparecem só como NPCs sem função (ou ausentes) |
| Área de combate | **Cripta Partida** (níveis de monstro 2–4) | Uma área jogável com início, salas e arena do chefe |
| Inimigos (4) | **Sentinela Oca** (eco de soldado), **Cão-de-Cinza** (fauna alterada), **Arauto de Pedra** (constructo), **Arqueiro Fantasma** (atirador) | Uma família por tipo; elite = qualquer tipo + 1 modificador ("escudo" ou "veloz") |
| Chefe opcional | **Guardião da Cripta**: martelo em cone telegrafado, escudo frontal que cai por trás ou com quebra de guarda; fase 2 invoca 2 Sentinelas | Arena com saída livre (o chefe é opcional para terminar a sessão, mas obrigatório para o domínio — ver RF-50) |
| Habilidades (3) | **Corte de Ferro** (inicial), **Investida** (nível 2), **Fenda de Pedra** (nível 3 no protótipo) | + esquiva (3 cargas) + 2 poções de vida. Barra com 4 espaços, 1 vazio |
| Equipamento | 5 posições (arma, elmo, peitoral, luvas, botas); 6 bases; 8 afixos | Subconjunto da matriz do demo |
| Loot | Raridades **Comum, Mágico, Raro** e **1 Único** (só do Guardião); Ouro e 1 material (Lascas) | Feixe de luz e cor por raridade |
| Expedição idle | Só na Cripta Partida depois de dominada; objetivo XP, Ouro ou Materiais; até 6 regras de IA; 1–12 h; as 8 regras rígidas | Simulada pelo ShatterCore ao abrir o jogo |
| Relógio | UTC Unix, `last_seen`, relógio voltando/adiantado | Sem conferência com a Steam nesta rodada |
| Save | 1 slot local em JSON, gravação segura, 3 backups, SHA-256, migração v1→v2 de exemplo | Configurações em arquivo separado |
| Idiomas | pt_BR e en, troca no menu | Fonte com acentos testada |
| Entrada | Teclado e mouse, remapeável, via Enhanced Input | Sem controle |
| Ferramentas | Acelerador de tempo (1 h de expedição = 10 s) e console de debug mínimo em build de desenvolvimento | |

### 2.2 Fora do escopo desta rodada

- Arqueiro, Mago, Assassino, Necromante; especializações; árvore passiva; respec.
- Livros, Páginas, ranks de habilidade e Sigilos de Suporte (as 2 habilidades extras são liberadas por nível, como simplificação provisória).
- Crafting com o Bram; compra de livros com a Irmã Odete; Fragmentos de Eco e Codex.
- Estrada das Lanternas e as demais 6 áreas do Ato I; os outros 3 chefes; endgame (Carta dos Marcos, Pedras de Rota, Predador dos Marcos).
- Integração com a Steam (conquistas, Steam Cloud, Rich Presence, overlay, `GetServerRealTime`), SteamPipe e CI de builds.
- Telemetria, Sentry, política de privacidade, demo como AppID separado.
- Arte e áudio finais (o protótipo usa placeholders com licença registrada), música, tremor de tela refinado, 8 direções.
- Teste de paridade com bot jogando a cena real em headless (fica para a próxima rodada; ver P-3).
- Espanhol, controle/Steam Deck, mais de um slot de save, segundo slot de expedição.

---

## 3. Requisitos funcionais

### 3.1 Atributos e modificadores
- **RF-01** Todo atributo é calculado por uma única fórmula: `(base + Σ planos) × (1 + Σ aumentados) × Π (1 + cada "mais")`.
- **RF-02** Modificadores têm tags (ataque, feitiço, corpo_a_corpo, projétil, área, fogo, frio, raio, físico); um modificador só vale para habilidades que têm todas as suas tags.
- **RF-03** O resultado fica em cache e só é recalculado quando algo muda (item, nível, efeito ganho ou perdido).
- **RF-04** Nenhum valor final é negativo; custos têm mínimo 0 e recargas mínimo 0,1 s.
- **RF-05** XP para o próximo nível = `100 + 60 × (nível − 1)^1,5`; cada nível dá vida e Ímpeto base da classe (valores em dados).

### 3.2 Cálculo de golpe
- **RF-06** Ordem fixa: dano base (habilidade ou arma) × coeficiente → modificadores por tag → crítico (multiplicador base 150%) → evasão (só ataques, teto 70%) → bloqueio (teto 50%) → armadura (só físico) → resistência elemental (teto 75%) → barreira → vida.
- **RF-07** A armadura reduz proporcionalmente menos os golpes grandes que os pequenos (fórmula definida pelo Tech Lead em `docs/tecnico/04_arquitetura.md`).
- **RF-08** Efeitos ao acertar: lentidão, quebra de guarda, ganho de Ímpeto (queimadura fica preparada em dados, sem uso no protótipo).
- **RF-09** Cada efeito tem duração, intervalo de tick e regra de acúmulo (renovar, acumular até N, só o mais forte).
- **RF-10** Gatilhos automáticos ("ao bloquear", "ao matar") têm recarga interna mínima de 0,25 s e não disparam outro efeito do mesmo tipo.

### 3.3 Combate em tempo real
- **RF-11** Lógica de combate em passo fixo (60 Hz), independente do FPS de renderização.
- **RF-12** Habilidade = dados (custo, recarga, preparação, impacto, recuperação, tags, coeficientes) + comportamento de forma (cone, avanço, área). O dano sempre passa pelo ShatterCore.
- **RF-13** Corte de Ferro: arco frontal curto, 0,4–0,6 s, gera Ímpeto. Investida: avanço com impacto na chegada. Fenda de Pedra: cone de fissuras para grupos.
- **RF-14** Ímpeto enche ao acertar e ao bloquear e esvazia fora de combate.
- **RF-15** Esquiva: 0,35 s, invulnerável nos primeiros 0,2 s, 3 cargas, cada uma recarrega em 1,5 s.
- **RF-16** Cada golpe acerta o mesmo alvo no máximo uma vez, salvo regra explícita.
- **RF-17** Juice mínimo: hitstop por entidade de 40–80 ms em golpes pesados e críticos; flash branco de 1 frame; knockback em comuns (elites resistem); números de dano com crítico maior; tremor de tela desligável.
- **RF-18** Morte do jogador: volta ao último checkpoint sem perder itens nem XP; na arena do chefe, a luta reinicia na hora.
- **RF-19** 2 poções de vida em teclas próprias, com cargas e recarga definidas em dados.

### 3.4 IA inimiga
- **RF-20** Máquina de estados: parado → perseguir → telegraph → atacar → recuperar.
- **RF-21** Sentinela Oca patrulha em grupo e ataca em fila; Cão-de-Cinza é rápido, cerca e foge com pouca vida; Arauto de Pedra é lento, com armadura alta e golpe forte telegrafado; Arqueiro Fantasma mantém distância e dispara.
- **RF-22** Elite = tipo base + 1 modificador ("escudo" ou "veloz"), com mais vida e nome/realce visível.
- **RF-23** Guardião da Cripta: tabela de padrões por fase; telegraph de 0,7–1,2 s sempre com forma no chão e som; escudo frontal bloqueia golpes de frente até ser quebrado ou contornado; fase 2 invoca 2 Sentinelas.
- **RF-24** Padrões do chefe com variação controlada por seed (não é sequência fixa).

### 3.5 Loot
- **RF-25** Tabelas de loot com pesos em dados; o sorteio usa o fluxo de RNG de loot.
- **RF-26** Comum = base + propriedade da base; Mágico = até 2 afixos; Raro = até 4 afixos; Único = atributos fixos + 1 efeito de build + 1 contrapartida.
- **RF-27** O Único do protótipo só cai do Guardião da Cripta, no jogo manual.
- **RF-28** Nomes de itens montados com gênero gramatical (base guarda o gênero, afixo tem forma masculina e feminina); nunca concatenar pedaços de frase.
- **RF-29** Drop com feixe de luz, cor e som por raridade; Único com coluna de luz própria.
- **RF-30** Inventário com 5 posições de equipamento, equipar/desequipar e comparação simples com o item equipado.

### 3.6 Expedição idle (as 8 regras rígidas)
- **RF-31 (Regra 1 — Só território dominado)** A expedição só pode ser iniciada em área que o personagem venceu na mão do início ao fim, incluindo o chefe.
- **RF-32 (Regra 2 — Fervor)** A patrulha rende a taxa base; o jogo manual mostra Fervor com XP ×3, Ouro e materiais ×1,25, chance de Raro ×2 e acesso ao Único. Idle ≈ 35% do XP/hora manual na mesma área (valores em dados).
- **RF-33 (Regra 3 — Teto de nível)** O XP do idle para de entrar quando o personagem passa 2 níveis acima do nível da área farmada.
- **RF-34 (Regra 4 — Sem itens de topo)** Único, livro de especialização, Sigilo raro e entrada de mapa nunca saem do idle; Raros com metade da chance e no máximo 4 por expedição.
- **RF-35 (Regra 5 — Cargas do Marco)** Cada hora gasta 1 carga; máximo 12 guardadas; limpar área na mão +1, vencer chefe +2, conquistar área nova +3; descanso +4 por dia real (UTC), sem acumular dias não reclamados.
- **RF-36 (Regra 6 — Vigor)** Horas 1–4 a 100%, 5–8 a 70%, 9–12 a 40% da taxa da patrulha; mostrado como barra de Vigor.
- **RF-37 (Regra 7 — Um por vez)** Só um personagem do save em expedição (o protótipo tem 1 personagem; a regra fica no ShatterCore).
- **RF-38 (Regra 8 — Risco real)** Build, equipamento e regras de IA ficam congelados num snapshot no início; falta de vida/poções faz o personagem recuar mais cedo; loot já obtido nunca é perdido.
- **RF-39** Configuração na Ilsa: área dominada, objetivo (XP, Ouro, Materiais), até 6 regras de IA em ordem (ex.: "poção abaixo de 35% de vida", "Fenda de Pedra se houver 3 ou mais inimigos"), duração 1–12 h limitada pelas cargas.
- **RF-40** A tela de configuração mostra previsão em faixa (ex.: "8–12 mil de XP, risco de recuo médio") calculada pelo simulador.
- **RF-41** O simulador resolve encontro por encontro, sem posição nem física, em passos de 0,1 s, usando o mesmo motor de regras do combate e IdleProfiles por habilidade.
- **RF-42** Recibo por encontro (resultado, duração, poções, XP, loot); o total é a soma dos recibos, com as taxas da seção 7 do plano aplicadas uma única vez.
- **RF-43** Habilidade sem IdleProfile bloqueia a expedição com mensagem clara; nunca usar equivalente genérico.
- **RF-44** Relatório do Tico: tempo efetivo, encontros vencidos, poções gastas, motivo da parada, loot, uma dica acionável e o convite "Jogar esta rota agora".
- **RF-45** Apresentação como bônus: nenhum número negativo ("-65% de XP") em nenhuma tela; o HUD manual mostra o ícone do Fervor e "+200% XP".

### 3.7 Relógio e tempo offline
- **RF-46** Início de expedição e `last_seen` gravados como tempo Unix em UTC.
- **RF-47** Ao abrir o jogo, o tempo simulado = min(agora − início, duração escolhida, 12 h).
- **RF-48** Se agora < `last_seen` − 5 min, a expedição encerra no último ponto conhecido, sem tempo extra, e o relatório informa o motivo.
- **RF-49** Adiantar o relógio nunca entrega mais do que a duração escolhida.

### 3.8 Domínio e progresso
- **RF-50** Domínio da Cripta = percorrer a área até o fim e vencer o Guardião na mesma conquista; ao vencer, o jogo instala o Marco de Retorno, concede as cargas (+2 chefe, +3 área nova) e libera a expedição na Ilsa.

### 3.9 Save e migração
- **RF-51** Save em JSON legível, 1 arquivo por slot e 1 de configurações; contém `save_version`, `content_version`, personagem, baú, domínios, cargas, `last_seen` e expedição em andamento (snapshot, seed, início, duração, status).
- **RF-52** Gravação segura: escrever `.tmp`, conferir, renomear; 3 backups rotativos; checksum SHA-256 no arquivo.
- **RF-53** Save corrompido → carregar o backup mais recente válido e avisar o jogador.
- **RF-54** Salvar ao trocar de área, ao coletar expedição, ao sair e a cada 5 min.
- **RF-55** Coleta sem duplicar: o status vira "coletada" no mesmo salvamento que adiciona o loot; reabrir após queda recalcula o mesmo resultado e entrega uma única vez.
- **RF-56** Migração encadeada `migrar_de_N_para_N+1`; o save guarda IDs estáveis em texto, nunca caminhos de asset.

### 3.10 UI e HUD
- **RF-57** HUD: retrato com moldura, barras de Vida e Ímpeto, faixa com nome da área, Ouro e Cargas do Marco no canto, barra inferior (habilidades, esquiva com cargas, 2 poções), números de dano.
- **RF-58** Telas: menu principal (Novo jogo / Continuar / Opções / Sair, versão visível no canto), inventário, configuração de expedição, relatório da expedição, opções (idioma, remapeamento, tremor de tela).
- **RF-59** Visual 3D estilizado conforme `docs/arte/03_design_system.md` e as folhas oficiais de `docs/arte/referencias-geracao/`. A UI é renderizada na resolução nativa com escala de DPI, e as cores da UI, das raridades, dos elementos e da névoa de cada área vêm de `docs/arte/03_design_tokens.json`.
- **RF-60** Ao abrir o jogo com expedição vencida, mostrar "o Tico está voltando..." enquanto o simulador roda, sem travar a interface.

### 3.11 Localização
- **RF-61** Nenhum texto fixo no código: todo texto visível vem de chave (ex.: `skill.warrior.iron_cut.name`) com colunas pt_BR e en.
- **RF-62** Idioma trocável no menu, persistido nas configurações; padrão = idioma do sistema, fallback en.
- **RF-63** A interface comporta o texto mais longo (pt_BR ≈ 30% maior que en) sem cortar.

### 3.12 Entrada
- **RF-64** Mapeamento padrão: WASD mover, mouse mira, botão esquerdo ataque básico, botão direito/Q/E habilidades, Espaço esquiva, 1 e 2 poções, I inventário, Esc menu.
- **RF-65** Toda entrada passa por ações nomeadas (Enhanced Input), nunca tecla fixa no código; todas as teclas remapeáveis com configuração salva.

**Total: 65 RF.**

---

## 4. Requisitos não funcionais

- **RNF-01 Determinismo** Mesma seed + mesmos dados + mesmo snapshot = resultado idêntico, bit a bit, em qualquer máquina suportada.
- **RNF-02 Fluxos de RNG separados** Combate, loot e eventos usam geradores distintos com seed = hash(seed_expedição, fluxo, índice_do_encontro); simular em 1 parte ou em 10 partes dá o mesmo resultado; mudar o combate não muda o loot sorteado por encontro.
- **RNF-03 Desempenho do simulador** 12 h de expedição (~720 encontros) em menos de 2 s num PC modesto; fora da thread de jogo.
- **RNF-04 Desempenho do jogo** 60 FPS estáveis na Cripta com até 30 inimigos ativos em PC de entrada (alvo final do plano: 80); carregamento da área < 3 s.
- **RNF-05 Robustez do save** Nenhuma perda de progresso por queda de energia, encerramento forçado ou save corrompido; migração nunca apaga dados.
- **RNF-06 Sem servidor** O jogo funciona 100% offline; nenhuma chamada de rede no protótipo.
- **RNF-07 Dados fora do código** Nenhum número de balanceamento em C++ ou Blueprint; tudo em CSV validado (IDs únicos, referências existentes, mín < máx, pesos > 0).
- **RNF-08 Independência do ShatterCore** O ShatterCore compila e testa sem nenhum header do Unreal (C++17 padrão, CMake).
- **RNF-09 Relógio não confiável** O relógio do PC é tratado como entrada potencialmente errada; nenhuma manipulação gera recompensa extra.
- **RNF-10 Versão de conteúdo** `content_version` gravado em cada save e em cada expedição.
- **RNF-11 Rastreabilidade** Versão do build visível no menu; log local rotativo.

**Total: 11 RNF.**

---

## 5. Critérios de aceite

Formato: checklist objetivo. A coluna "Ver." indica onde se verifica.

### 5.1 Atributos, golpe e efeitos

| ID | Critério | Ver. |
|---|---|---|
| RF-01 | Dado base 100, planos +10 e +20, aumentados +20% e +30%, "mais" 10% e 20%, então o valor = 130 × 1,5 × 1,1 × 1,2 = 257,4 (tolerância 1e-6) | SC |
| RF-02 | Modificador "+15% dano de projétil" não altera Corte de Ferro (sem tag projétil); "+15% corpo_a_corpo" altera | SC |
| RF-03 | Duas leituras seguidas sem mudança não recalculam (contador de recálculo inalterado); trocar um item recalcula 1 vez | SC |
| RF-04 | Com redução de custo de 200% o custo é 0; com redução de recarga de 99% a recarga é 0,1 s; nenhum atributo final < 0 em 10 mil combinações aleatórias | SC |
| RF-05 | XP para sair do nível 1 = 100; do nível 2 = 160; do nível 3 ≈ 269,7 (arredondamento definido em dados); do nível 5 = 100 + 60×4^1,5 = 580 | SC |
| RF-06 | Teste com alvo de evasão 90%: taxa observada em 100 mil ataques = 70% ± 0,5; resistência 100% é tratada como 75%; bloqueio 80% vira 50%; feitiço ignora evasão; dano físico passa pela armadura e elemental não | SC |
| RF-06 | Crítico com multiplicador base: golpe de 100 crítico = 150 antes das defesas | SC |
| RF-07 | Para a mesma armadura, a fração reduzida de um golpe de 1000 é menor que a de um golpe de 100 (propriedade monotônica testada em 1000 pares) | SC |
| RF-08/09 | Lentidão "renovar" reinicia a duração; efeito "acumular até 3" nunca passa de 3; "só o mais forte" mantém o maior valor | SC |
| RF-10 | Dois gatilhos "ao bloquear" no mesmo instante disparam 1 vez; um gatilho não dispara outro do mesmo tipo (sem laço em 10 mil ticks) | SC |

### 5.2 Combate, IA e chefe

| ID | Critério | Ver. |
|---|---|---|
| RF-11 | A 30 FPS e a 144 FPS, um mesmo roteiro de entrada contra um Arauto produz o mesmo dano total (lógica em passo fixo) | SC+UE |
| RF-12 | Nenhum cálculo de dano no módulo UE fora de chamadas ao ShatterCore (revisão de código + busca textual) | UE |
| RF-13 | Corte de Ferro tem ciclo total entre 0,4 e 0,6 s; Fenda de Pedra atinge ≥ 3 inimigos agrupados à frente; Investida aplica dano na chegada | UE |
| RF-14 | Acertar e bloquear aumentam Ímpeto; após o tempo fora de combate definido em dados, Ímpeto cai até 0 | SC+UE |
| RF-15 | Golpe recebido aos 0,1 s da esquiva causa 0 de dano; aos 0,3 s causa dano; 4ª esquiva seguida é negada; 1 carga volta após 1,5 s | SC+UE |
| RF-16 | Corte de Ferro contra 1 inimigo grande registra 1 acerto por golpe | UE |
| RF-17 | Checklist visual: hitstop perceptível em crítico, flash branco, knockback em comum e não em elite, número de crítico maior, opção que desliga o tremor | UE |
| RF-18 | Morrer na Cripta volta ao checkpoint com XP e itens iguais aos de antes da morte; morrer no Guardião reinicia a luta em < 2 s | UE |
| RF-19 | Poção usada com 0 cargas não faz nada e dá aviso; cargas e recarga batem com o CSV | SC+UE |
| RF-20/21 | Cada um dos 4 inimigos passa pelos 5 estados (log de debug); Cão-de-Cinza foge abaixo do limiar de vida; Arqueiro Fantasma mantém distância mínima | UE |
| RF-22 | Elite "escudo" e elite "veloz" aparecem com realce e nome, e têm mais vida que o comum (valor do CSV) | UE |
| RF-23 | Todo ataque do Guardião tem telegraph de 0,7–1,2 s com forma no chão e som; golpe de frente no escudo erguido causa 0 de dano à vida; fase 2 começa no limiar de vida definido e invoca exatamente 2 Sentinelas | SC+UE |
| RF-24 | Mesma seed → mesma sequência de padrões; seeds diferentes → sequências diferentes em ≥ 90% de 100 seeds | SC |

### 5.3 Loot e inventário

| ID | Critério | Ver. |
|---|---|---|
| RF-25 | 1 milhão de sorteios por tabela: frequência observada de cada entrada dentro de ±1% relativo do peso esperado (ou ±3 desvios-padrão) | SC |
| RF-26 | Nenhum Mágico gerado com > 2 afixos, nenhum Raro com > 4, nenhum afixo repetido no mesmo item, todos os valores dentro da faixa | SC |
| RF-27 | Em 1 milhão de sorteios de tabelas que não são do Guardião, 0 Únicos | SC |
| RF-28 | Todos os pares base × afixo geram nome com concordância correta em pt_BR (ex.: "Lâmina ... Rachada" e não "Lâmina ... Rachado"); revisão humana de uma amostra de 20 nomes | SC+UE |
| RF-29 | Cada raridade tem cor de feixe distinta; o Único tem coluna e som próprios | UE |
| RF-30 | Equipar um item muda os atributos exibidos no mesmo quadro; desequipar volta ao valor anterior | UE |

### 5.4 Expedição idle (8 regras)

| ID | Critério | Ver. |
|---|---|---|
| RF-31 | Dado um save sem domínio da Cripta, quando se tenta iniciar expedição, então o ShatterCore recusa com motivo "área não dominada"; limpar a área sem vencer o Guardião continua recusando | SC+UE |
| RF-32 | Mesmo build e mesma área: XP/hora do simulador sem Fervor ≈ 35% (±5 p.p.) do XP/hora com os multiplicadores do Fervor aplicados aos mesmos recibos; o Fervor multiplica Ouro e materiais por exatamente 1,25 | SC |
| RF-33 | Personagem nível 6 na Cripta (nível 4): o idle concede 0 XP; nível 5 ganha XP até atingir o nível 6 e para | SC |
| RF-34 | Em 10 mil expedições de 12 h com seeds diferentes: 0 Únicos, 0 livros de especialização, 0 Sigilos raros, 0 entradas de mapa; nenhuma expedição com > 4 Raros; taxa de Raro por encontro = 50% da manual (±10% relativo) | SC |
| RF-35 | Começar com 12 cargas e ganhar +1 resulta em 12; expedição de 5 h com 3 cargas é recusada ou limitada a 3 h; descanso dá +4 no novo dia UTC e 3 dias sem abrir o jogo dão só +4 | SC |
| RF-36 | Expedição de 12 h com encontros idênticos: rendimento das horas 5–8 = 70% e 9–12 = 40% do rendimento das horas 1–4 (±1%) | SC |
| RF-37 | Tentar iniciar uma 2ª expedição com outra ativa é recusado | SC |
| RF-38 | Trocar o equipamento depois de iniciar a expedição não altera o resultado simulado; build sem poções e com pouca vida recua mais cedo que build com poções (motivo de parada registrado); loot dos encontros vencidos antes do recuo é entregue | SC |
| RF-39 | É impossível salvar uma configuração com 7 regras ou duração fora de 1–12 h; regras avaliadas em ordem, vale a primeira válida | SC+UE |
| RF-40 | A faixa prevista contém o resultado real em ≥ 80% de 1000 expedições simuladas | SC |
| RF-41/42 | Total da expedição = soma dos recibos com taxas aplicadas 1 vez (teste compara soma manual dos recibos com o total) | SC |
| RF-43 | Build com habilidade sem IdleProfile → expedição bloqueada com a mensagem localizada correspondente | SC+UE |
| RF-44 | O relatório exibe os 6 campos e a dica; o botão "Jogar esta rota agora" leva à Cripta | UE |
| RF-45 | Busca nas strings pt_BR e en de UI de expedição/HUD: nenhum valor percentual negativo; HUD manual mostra ícone do Fervor e "+200% XP" | SC+UE |

### 5.5 Relógio, domínio e save

| ID | Critério | Ver. |
|---|---|---|
| RF-46/47 | Expedição de 4 h iniciada há 10 h simula 4 h; de 12 h iniciada há 30 h simula 12 h; mudar o fuso horário do SO não muda o resultado | SC |
| RF-48 | `last_seen` = T, agora = T − 6 min → expedição encerra no último ponto conhecido, motivo "relógio voltou"; agora = T − 4 min → segue normal | SC |
| RF-49 | Adiantar o relógio 3 dias durante uma expedição de 2 h entrega exatamente o resultado de 2 h | SC |
| RF-50 | Vencer o Guardião após percorrer a Cripta grava o domínio, soma +5 cargas (respeitando o teto 12) e libera a opção na Ilsa | SC+UE |
| RF-51 | Save gerado passa no validador de esquema e contém todos os campos listados; abre em editor de texto legível | SC |
| RF-52 | Interromper a gravação após escrever o `.tmp` (injeção de falha) mantém o save anterior íntegro; após 5 salvamentos existem exatamente 3 backups; alterar 1 byte faz o checksum falhar | SC |
| RF-53 | Save principal corrompido → carrega o backup mais recente válido e sinaliza aviso; se todos corrompidos, nunca sobrescreve sem confirmação | SC+UE |
| RF-54 | Com o acelerador de debug, 5 min de jogo geram 1 autosave; trocar de área e sair também salvam | UE |
| RF-55 | Simular queda entre "loot calculado" e "save gravado": ao reabrir, o loot aparece 1 vez; coletar duas vezes a mesma expedição entrega 1 vez | SC |
| RF-56 | Save v1 de exemplo (guardado em `tests/`) carrega na v2 sem perda de campos; save só contém IDs como `skill.warrior.iron_cut`, nenhum caminho `/Game/...` | SC |

### 5.6 UI, localização e entrada

| ID | Critério | Ver. |
|---|---|---|
| RF-57 | Checklist do HUD com os 7 elementos presentes em 1080p, sem sobreposição | UE |
| RF-58 | Cada tela abre, fecha e volta à anterior por mouse e por Esc; a versão aparece no menu | UE |
| RF-59 | Capturas em 1920×1080 e 1280×800 (Steam Deck) mostram a UI nítida e legível; as cores da UI batem com os tokens; o Guerreiro e os inimigos da Cripta são reconhecíveis pelas folhas oficiais | UE |
| RF-60 | Simulação de 12 h ao abrir o jogo não congela a tela (animação continua) | UE |
| RF-61 | Busca no código do módulo UE e do ShatterCore: 0 literais de texto visível; todas as chaves usadas existem nas colunas pt_BR e en (validador) | SC |
| RF-62 | Trocar o idioma no menu atualiza todas as telas sem reiniciar e persiste após reabrir | UE |
| RF-63 | Todas as telas em pt_BR sem texto cortado ou estourando moldura; ç, ã, õ, á, é, ê aparecem corretamente na fonte | UE |
| RF-64 | Cada ação do mapeamento padrão funciona no primeiro uso de um save novo | UE |
| RF-65 | Remapear a esquiva para Shift funciona, persiste após reiniciar e o Espaço deixa de esquivar; nenhum `EKeys::` fixo fora da configuração padrão (busca textual) | UE |

### 5.7 Não funcionais

| ID | Critério | Ver. |
|---|---|---|
| RNF-01 | A mesma expedição (seed fixa) simulada 100 vezes gera 100 resultados com hash idêntico; o hash bate entre build Debug e Release no Linux (e no Windows quando o dono rodar) | SC (+UE no Windows) |
| RNF-02 | Simular 12 h em 1 chamada e em 10 chamadas sequenciais (retomando do estado salvo) → resultado idêntico; mudar um coeficiente de dano não muda o loot sorteado nos encontros que terminam igual | SC |
| RNF-03 | Benchmark de 12 h: < 2 s no workspace Linux (Release); medição registrada em `12_performance.md`; no UE, a simulação roda fora da game thread | SC+UE |
| RNF-04 | `stat fps` ≥ 60 estável na Cripta com 30 inimigos num PC de entrada indicado pelo dono; carga da Cripta < 3 s | UE |
| RNF-05 | Coberto por RF-52, RF-53, RF-55, RF-56; adicionalmente, 1000 ciclos salvar/carregar sem divergência de conteúdo | SC |
| RNF-06 | O protótipo roda com a rede desligada; nenhum módulo de rede referenciado no `.Build.cs` além do padrão do motor | UE |
| RNF-07 | Validador de dados passa em todos os CSV; um CSV com ID duplicado, referência inexistente, mín > máx ou peso 0 faz o validador falhar com mensagem clara; busca textual sem números de balanceamento no código | SC |
| RNF-08 | `cmake --build` e `ctest` passam no Linux sem o Unreal instalado; 0 includes de headers do Unreal em `ShatterCore/` | SC |
| RNF-09 | Coberto por RF-46 a RF-49 | SC |
| RNF-10 | Save e expedição gravados contêm `content_version`; save com `content_version` maior que o do jogo é recusado com aviso, sem ser alterado | SC |
| RNF-11 | Versão visível no menu; arquivo de log criado e rotacionado | UE |

### 5.8 Aceite global da rodada
- [ ] Todos os critérios **[SC]** passando no `ctest` (QA registra em `docs/requisitos-qa/10_qa.md`).
- [ ] Projeto UE5 revisado por leitura sem defeito bloqueante (`11_code_review.md`).
- [ ] Roteiro manual do dono para os critérios **[UE]**, com resultado anotado em `13_aceite.md` (pode ficar pendente até o dono abrir o editor).
- [ ] Teste de fogo do pilar 1: o dono joga 30 s contra Sentinelas na Cripta e descreve o combate como satisfatório (portão de "Combate sem graça" do plano).

---

## 6. Desvios do plano causados pela troca para UE5 (visão de produto)

> Nota (16/10/2026): o motor passou para a Unity 6.3 LTS. Esta tabela registra os desvios da fase UE5 e fica como histórico; o D-10 não se aplica mais (Unity Personal, sem royalty).

| # | Plano (Godot 4) | Agora (UE5) | Impacto no produto |
|---|---|---|---|
| D-1 | Godot 4 2D em pixel art, renderer Compatibility, foco em PCs fracos | UE 5.8 em 3D estilizado pintado à mão: Forward Shading com MSAA, sem Lumen, Nanite nem Virtual Shadow Maps (`docs/arte/08_decisoes_visual_3d.md` e `docs/tecnico/04_arquitetura.md`) | Requisito mínimo de hardware sobe; a meta "60 FPS com GPU integrada" vira risco a medir cedo (RNF-04) |
| D-2 | Build < 500 MB | Build UE5 base é maior; meta mantida, mas sob vigilância | Pode exigir corte de módulos do motor; afeta download e Steam Deck no 1.0 |
| D-3 | Regras em GDScript RefCounted, um único motor | Regras em **ShatterCore** C++17 puro, usado pelo módulo UE e pelo simulador | Fortalece o princípio "um único motor de regras"; testes rodam sem o editor |
| D-4 | Testes GUT, parity bot em Godot headless | `ctest` no ShatterCore + Automation do UE; parity bot adiado | Nesta rodada não há prova de paridade combate × simulador; IdleProfiles ficam com valores provisórios marcados como "não calibrados" |
| D-5 | InputMap | Enhanced Input (ações nomeadas) | Equivalente; adicionar controle no 1.0 continua barato |
| D-6 | `tr()` + CSV de tradução | Tabelas de texto/Localization do UE alimentadas por CSV (chave, pt_BR, en) | Equivalente para o jogador; pipeline de tradução muda para a equipe |
| D-7 | Save em `%APPDATA%/EchoesOfTheShatter` via `use_custom_user_dir` | Pasta de save própria do jogo definida no UE (proposta: `%LOCALAPPDATA%/EchoesOfTheShatter/Saved/`) | Configurar o Auto-Cloud da Steam para o novo caminho quando a Steam entrar |
| D-8 | GodotSteam, Sentry para Godot | Steamworks/OnlineSubsystemSteam e plugin Sentry para UE (fora desta rodada) | Sem impacto no protótipo |
| D-9 | Física a 60 Hz em `_physics_process` | Tick do UE é variável; combate em passo fixo dentro do ShatterCore | Necessário para RF-11 e para a paridade futura |
| D-10 | Godot sem royalties | EULA da Epic: royalty sobre receita bruta acima do limite da Epic por produto | Entra no cálculo de preço e receita; ver P-5 |
| D-11 | Recursos tipados (`.tres`) + `import_tables.gd` | DataTables do UE importadas dos mesmos CSV + `tools/dados/validate_data.py` | Planilha continua a fonte de balanceamento |
| D-12 | Iteração rápida no editor leve | Editor e compilação C++ mais pesados | Protótipo do dono depende de compilar no Windows; prazo da F1 deve ser remedido |

Simplificações de escopo desta rodada que **não** são causadas pelo UE5 (registradas para não virarem regra): habilidades liberadas por nível em vez de Livros; Fenda de Pedra no nível 3 em vez de 5; sem conferência de relógio com a Steam.

---

## 7. Perguntas em aberto para o dono do projeto

1. **P-1 Visual 2D no UE5:** respondida em 16/10/2026. O dono escolheu 3D estilizado pintado à mão, no estilo das referências aprovadas, e não pixel art (ver `docs/arte/08_decisoes_visual_3d.md`).
2. **P-2 Chefe e domínio:** respondida em 16/10/2026. O Guardião é obrigatório nesta rodada: dominar a Cripta é vencer o Guardião (Regra 1 mantida).
3. **P-3 Paridade:** respondida em 16/10/2026. O teste de paridade fica para a próxima rodada; os IdleProfiles usam valores estimados, marcados como não calibrados (selo "Estimativa" na tela).
4. **P-4 PC de referência:** respondida em 16/10/2026. O "PC de entrada" é genérico: GPU de 4 GB do nível GTX 1050 Ti/RX 570, CPU de 4 núcleos, 8 GB de RAM, 1080p (ver `docs/tecnico/04_arquitetura.md`, seção 18). O Steam Deck é medido como alvo à parte.
5. **P-5 Motor e licença:** respondida em 16/10/2026. O motor passou para a Unity 6.3 LTS com a licença Unity Personal, sem royalty nem taxa por instalação. O dono está ciente de que a Personal vale enquanto a receita ou o investimento dos últimos 12 meses ficar abaixo de US$ 200 mil; acima disso, é preciso a Unity Pro.
