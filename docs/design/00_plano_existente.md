

# Echoes of the Shatter — Plano Steam v2.0

2026-10-13 · @william

> **Atualização de 16/10/2026:** o visual e o motor deste plano foram substituídos. O jogo agora é 3D estilizado pintado à mão no Unreal Engine 5.8 (ver `docs/arte/08_decisoes_visual_3d.md`, `docs/tecnico/04_arquitetura.md`, `docs/arte/03_design_system.md` e `docs/arte/referencias-geracao/`). As partes sobre pixel art e Godot ficam como histórico: o pitch da Steam ("dark pixel-art ARPG"), a ficha técnica, as especificações de arte da seção 9 e a parte técnica da seção 10. O pitch em inglês precisa ser reescrito antes da página da Steam. As regras de jogo, o conteúdo e o escopo continuam valendo.

## 1. Visão geral
Echoes of the Shatter é um ARPG single-player em pixel art, vendido na Steam por preço fechado, no qual você conquista cada área jogando e depois manda o personagem farmá-la sozinho enquanto o jogo está fechado. Esta versão 2.0 substitui o plano 1.1: sai a Solana, o marketplace em USDC e o servidor obrigatório; o lançamento é em Acesso Antecipado com 3 classes e 1 ato.
Nome: Echoes of the Shatter é o nome único do jogo em todos os idiomas, inclusive na página da Steam em português. Na história, o evento que partiu o Arquivo passa a se chamar o Shatter. Uma busca na web em 13/10/2026 não achou jogo com o mesmo nome (o mais parecido é Echoes of a Shattered Sky, no itch.io). Ainda falta checar marca no INPI e no USPTO.
Pitch em uma frase: "Conquiste na mão. Domine a rota. Deixe seu herói farmar enquanto você vive."
Pitch para a página da Steam (inglês): A dark pixel-art ARPG where every dungeon you conquer by hand becomes a route your hero can farm while you're away. Plan the expedition, read the report, sharpen the build, and take on the next boss yourself.

### Pilares de design

Pilar

O que significa na prática

Teste para saber se está funcionando

Conquistar pela ação

Toda área e todo chefe novo exigem jogar na mão; o idle nunca abre conteúdo

Jogadores preferem jogar a próxima área em vez de só coletar expedições

Build com identidade

Livros ensinam habilidades, Sigilos as modificam, itens mudam como você joga

Três builds da mesma classe se jogam de forma visivelmente diferente

Planejar o retorno

A expedição é um pequeno quebra-cabeça: rota, regras de IA, poções, duração

O relatório de expedição gera uma decisão (trocar item, ajustar regra)

Respeitar o tempo

Sessão curta de 5 min já rende progresso; sessão longa rende conquista

Jogador com 15 min por dia continua progredindo e voltando

### Público
Principal: fãs de ARPG (Diablo, Path of Exile, Last Epoch, Grim Dawn) com pouco tempo livre, que gostam de build mas não conseguem jogar 3 horas por noite.
Secundário: fãs de idle e incremental na Steam que querem mais ação e decisão do que só números subindo.
Idioma: português e inglês desde o primeiro demo; espanhol no Acesso Antecipado se o orçamento permitir.

### Ficha técnica

Item

Decisão

Plataforma

PC Windows na Steam; Steam Deck verificado como meta do 1.0

Motor

Godot 4 (2D), versão fixada no início do projeto

Modo

Single-player offline; sem conta, sem servidor

Câmera

Isométrica 3/4, pixel art detalhado (ver referência na seção 9)

Controles

Só teclado e mouse no demo e no Acesso Antecipado; controle e Steam Deck avaliados para o 1.0

Modelo de negócio

Preço fechado, faixa de US$ 12–15 no Acesso Antecipado (R$ 35–45 com preço regional); sem microtransações

Monetização extra (opcional)

Pacote de apoiador com trilha sonora e artbook; cosméticos só no 1.0, nunca poder

Blockchain, NFT, cripto

Descartado. A Steam proíbe jogos que emitem ou negociam cripto/NFT

## 2. Escopo do Acesso Antecipado
O Acesso Antecipado lança com Guerreiro, Arqueiro e Mago, o Ato I completo (8 áreas, 4 chefes) e um endgame curto de 3 mapas em 5 tiers. Isso cobre os três estilos clássicos (corpo a corpo, distância e magia) e corta cerca de 70% do conteúdo previsto no plano 1.1.

### Por que essas 3 classes
Guerreiro, Arqueiro e Mago são a tríade que qualquer jogador entende em 2 segundos olhando a capa.
As três são as mais simples de simular no idle: nenhuma depende de lacaios nem de posicionamento muito fino.
Assassino (sangramento e veneno) e Necromante (lacaios) ficam para atualizações de conteúdo. Cada classe nova vira um evento de marketing.

### Matriz de conteúdo

Conteúdo

Demo (Next Fest)

Acesso Antecipado

1.0 (meta)

Classes

1 (Guerreiro)

3

5

Especializações

0

6 (2 por classe)

10

Habilidades ativas

4

24 (8 por classe)

50

Sigilos de Suporte

3

12

30

Nós da árvore passiva

0

60 (árvore compartilhada)

150

Nível máximo

8

30

60

Posições de equipamento

5

8

10

Bases de equipamento

10

30

80

Afixos

12

40

80

Únicos

1

12

25

Épicos curados

0

0 (só procedurais)

25

Áreas de campanha

2 (Estrada + Cripta)

8 (Ato I)

24 (3 atos)

Chefes

1

4 de campanha + 1 de endgame

17

Mapas de endgame

0

3 layouts × 5 tiers

12 × 10

Duração estimada

30–45 min

8–12 h de campanha + endgame

25 h+

### O que fica fora do Acesso Antecipado
Multiplayer (coop), troca entre jogadores, marketplace e qualquer servidor online.
Assassino, Necromante, Atos II e III.
Temporadas e rankings.
Épicos curados e Relíquias (o catálogo do plano 1.1 fica guardado como banco de ideias).

### O que muda nas regras ao virar single-player

Regra do plano 1.1

Motivo original

Nova regra

Todo item negociável, nada vinculado

Mercado em USDC

Não há comércio; o baú é compartilhado entre os personagens do save

Servidor autoritativo e PostgreSQL

Antifraude financeira

Save local; o jogador que trapaceia só engana a si mesmo

Livro do tutorial não pode ser item

Evitar farm de contas

O tutorial dá um livro de verdade

Ouro sem conversão, Gemas = USDC

Economia real

Só Ouro e materiais de crafting

Uma atividade produtora por conta

Limitar emissão de ativos

Um personagem em expedição por vez (no AA); mais slots como recompensa de progresso

## 3. Mundo e narrativa
O mundo de Aural guardava toda a sua memória no Arquivo Vivo; quando o Arquivo se partiu (o Shatter), as lembranças viraram matéria e passaram a se repetir sozinhas. O jogador é um Recuperador, alguém capaz de absorver memórias sem se perder nelas. Esta seção preenche o que o plano 1.1 deixava em aberto: o que foi o Shatter, quem é o antagonista e quem vive no refúgio.

### O Shatter
Antes: o Arquivo Vivo era uma rede de torres que guardava técnicas, ofícios e experiências. Qualquer pessoa podia aprender a forjar ou a curar "lendo" uma memória.
O evento: a Arquivista-Mor tentou gravar uma memória perfeita, o dia em que ninguém em Aural sofreu, e mantê-la tocando para sempre. O Arquivo não aguentou e se partiu.
Depois: fragmentos de memória caíram como estilhaços. Onde caem, as coisas repetem gestos do passado: soldados mortos continuam a patrulhar, máquinas obedecem a mestres que não existem mais, animais imitam pessoas.

### O tema
Repetição contra mudança. Os inimigos são memórias presas em ciclos. O jogador também repete rotas (o idle), mas com propósito: cada volta o deixa mais forte. Assim o idle faz parte da história, não é só uma mecânica.

### Antagonista: Vespéria, a Arquivista-Mor
Ela não morreu no Shatter: virou parte do Arquivo. Quer remontar as torres e terminar o que começou, prendendo Aural inteira num único dia feliz e eterno. Não é má de forma caricata. Perdeu alguém e acredita que esquecer a dor vale mais que viver. No Ato I ela aparece só como voz e reflexo; a luta final fica para o Ato III.

### Refúgio do Marco (hub)
Uma antiga estação de lanternas onde os sobreviventes se abrigam. Cresce visualmente conforme o Ato avança.

NPC

Função no jogo

Personalidade

Ilsa, a Cartógrafa

Mapa, Marcos de Retorno, expedições

Prática e irônica; mapeia o que mudou desde o Shatter

Bram, o Ferreiro

Crafting e melhorias

Perdeu a memória do próprio ofício e reaprende junto com o jogador

Irmã Odete, a Leitora

Livros, Sigilos e árvore passiva

Ex-aprendiz de Vespéria; sabe mais do que conta

Tico, o Mensageiro

Relatório das expedições e entrega do loot

Criança que corre entre os Marcos; alívio cômico

### Ato I: Vozes sob a Pedra (níveis 1–15)
O jogador chega à Estrada das Lanternas procurando a origem de um sino que toca sozinho toda noite. Descobre que ele chama memórias de volta à vida e que alguém o está tocando de propósito.
Estrada das Lanternas (níveis 1–2): tutorial de movimento, ataque e esquiva. Encontro com Ilsa.
Cripta Partida (2–4): primeiro livro, primeiro chefe. Chefe: Guardião da Cripta, um cavaleiro que ainda protege um rei que não está mais lá. Ao vencê-lo, o jogador instala o primeiro Marco de Retorno e libera a primeira expedição.
Pedreira dos Ecos (4–6): inimigos em grupo e terreno perigoso. Introduz o crafting com Bram.
Ponte do Sino (6–7): trecho estreito com atiradores. Primeira pista de Vespéria. Chefe: Tecelã de Cascalho, uma aranha de pedra que recria a ponte enquanto luta.
Armazém de Cinzas (7–9): área opcional de saque, com baús trancados e elites.
Pátio dos Marcos (9–11): escolha da especialização (Prova do Marco). Chefe: Carrasco do Voto, que executa quem quebra promessas antigas.
Túneis do Voto (11–13): masmorra mais longa, com sigilos raros.
Mirante Partido (13–15): Chefe final do Ato: Vigia do Sino, a memória do sineiro presa no momento do Shatter. Vencer revela o reflexo de Vespéria e abre o endgame.

## 4. Classes
Cada classe tem um recurso próprio, 8 habilidades no Acesso Antecipado e 2 especializações escolhidas no nível 10. Qualquer classe pode aprender livros básicos de outra se cumprir os requisitos, mas habilidades de especialização são exclusivas.

Classe

Fantasia

Recurso

Fraqueza

Especializações

Guerreiro

Muralha que vira martelo

Ímpeto: enche ao acertar e ao bloquear, esvazia fora de combate

Precisa chegar perto; golpes pesados deixam janela vulnerável

Bastião (escudo, bloqueio, retaliação) · Ruptor (duas mãos, quebra de guarda, impacto em área)

Arqueiro

Caçador paciente que nunca erra a presa

Foco: regenera rápido parado, devagar em movimento

Pouca defesa; distância é a armadura

Rastreador (marca, tiro preciso, chefes) · Armadilheiro (armadilhas, redes, controle de grupo)

Mago

Estudioso que dobra o Arquivo

Mana: regeneração constante, reserva alta

Frágil; feitiços fortes têm tempo de conjuração

Convergente (alternar fogo, gelo e raio para reações) · Canalizador (feitiços sustentados e barreira)

### Guerreiro

Habilidade

Desbloqueio

O que faz

Corte de Ferro

Inicial

Arco frontal curto; gera Ímpeto

Investida

Livro, nível 2

Avanço com impacto na chegada

Escudada

Livro, nível 3

Golpe que acumula quebra de guarda e atordoa comuns

Fenda de Pedra

Livro, nível 5

Cone de fissuras para limpar grupos

Postura Firme

Livro, nível 7

Reduz dano e empurrão recebidos por 4 s

Clamor de Aço

Livro, nível 9

Grito que enfraquece o ataque de inimigos próximos

Retaliação

Bastião, nível 10

Contra-ataque forte liberado após bloquear

Golpe do Shatter

Ruptor, nível 10

Impacto lento e devastador contra guarda quebrada

### Arqueiro

Habilidade

Desbloqueio

O que faz

Disparo Reto

Inicial

Flecha simples e rápida

Flecha Fendida

Livro, nível 2

Divide em 3 ao acertar o primeiro alvo

Recuo Ágil

Livro, nível 3

Salto para trás disparando

Marca da Trilha

Livro, nível 5

Marca um alvo: +dano e revela fraquezas

Chuva de Farpas

Livro, nível 7

Saraivada numa área por 3 s

Rede de Caça

Livro, nível 9

Prende inimigos comuns numa área

Tiro de Vigília

Rastreador, nível 10

Disparo carregado com dano enorme em alvo marcado

Círculo de Armadilhas

Armadilheiro, nível 10

Instala 3 armadilhas que explodem em sequência

### Mago

Habilidade

Desbloqueio

O que faz

Faísca Guiada

Inicial

Projétil elétrico que persegue o alvo

Lança de Gelo

Livro, nível 2

Projétil frio que desacelera

Brasa Errante

Livro, nível 3

Bola de fogo com explosão e queimadura

Barreira de Vidro

Livro, nível 5

Escudo de absorção temporário

Passagem Arcana

Livro, nível 7

Teleporte curto

Pulso de Tempestade

Livro, nível 9

Descarga em cadeia a partir do alvo

Prisma Elemental

Convergente, nível 10

Próximo feitiço de elemento diferente causa uma reação

Raio do Arquivo

Canalizador, nível 10

Feixe canalizado que fica mais forte quanto mais tempo dura
Regra de barra: 4 habilidades equipadas no demo, 6 no Acesso Antecipado, mais esquiva e 2 poções em teclas próprias. Trocar especialização custa Ouro no Refúgio, sem perder livros aprendidos.

## 5. Combate e sensação
O combate precisa ser gostoso antes de qualquer outro sistema existir: se bater num esqueleto na Cripta não for satisfatório em 30 segundos, nada mais salva o jogo. Esta seção define a sensação de jogar (o "game feel"), que faltava no plano 1.1.

### Ritmo
Sala típica: 15–30 s de combate, 5–10 s de respiro e coleta.
Ataque básico: 0,4–0,6 s por golpe. Habilidades fortes de 0,8–1,2 s com preparação visível.
Esquiva: 0,35 s com invulnerabilidade nos primeiros 0,2 s; custa 1 de 3 cargas, cada carga recarrega em 1,5 s.
Telegraph de chefe: 0,7–1,2 s, sempre com forma no chão e som.

### Checklist de "juice" (impacto)
Hitstop de 40–80 ms em golpes pesados e críticos
Inimigo pisca em branco por 1 frame ao ser atingido
Knockback curto em inimigos comuns; elites resistem
Tremor de tela leve só em impactos grandes (com opção de desligar)
Números de dano com tamanho por importância (crítico maior)
Partículas de poeira e faíscas no contato
Som de impacto diferente por tipo: carne, osso, pedra, metal
Morte de inimigo com animação curta e corpo que se desfaz em estilhaços dourados
Drop com som e brilho por raridade; Único tem coluna de luz e som próprio

### Famílias de inimigos do Ato I

Família

Exemplos

Comportamento

O que ensina

Ecos de soldado

Sentinela Oca, Lanceiro Repetido

Patrulham em grupo; atacam em fila

Agrupar e usar área

Fauna alterada

Cão-de-Cinza, Corvo Imitador

Rápidos, cercam, fogem com pouca vida

Priorizar alvos e controlar distância

Constructos

Arauto de Pedra, Prensa Viva

Lentos, armadura alta, golpe forte telegrafado

Quebra de guarda e esquiva no tempo certo

Atiradores

Arqueiro Fantasma, Lança-Faiscas

Ficam longe e disparam

Fechar distância ou interromper

Elites

Qualquer família + 1 ou 2 modificadores (escudo, veloz, explode ao morrer)

Mais vida e um truque

Ler o modificador antes de atacar

### Chefes do Ato I

Chefe

Área

Mecânica central

Fases

Guardião da Cripta

Cripta Partida

Golpe de martelo em cone (o da arte conceitual); escudo frontal que só cai por trás ou com quebra de guarda

2: na segunda invoca 2 Sentinelas

Tecelã de Cascalho

Ponte do Sino

Destrói e reconstrói pedaços da ponte; o chão seguro muda

2

Carrasco do Voto

Pátio dos Marcos

Marca o jogador; se o jogador atacar durante a marca, toma dano refletido

3

Vigia do Sino

Mirante Partido

O sino toca e repete os 3 últimos ataques do jogador contra ele

3
Morte: volta ao último checkpoint sem perder itens nem XP. Na arena de chefe, reinicia a luta na hora.

## 6. Progressão, loot e crafting
O personagem cresce em cinco eixos separados: nível, árvore passiva, livros e ranks de habilidade, equipamento e domínio de rotas. Os itens mais desejados (Únicos, Sigilos raros e livros de especialização) só caem jogando na mão.

### Nível e árvore
Nível máximo no Acesso Antecipado: 30. Ato I cobre 1–15; endgame 15–30.
Curva de XP: XP para o próximo nível = 100 + 60 × (nível − 1)^1,5, ajustada em playtest para a campanha durar 8–12 h.
Por nível: 1 ponto passivo + vida e recurso base da classe. Sem pontos de atributo manuais no Acesso Antecipado: menos menus, mais decisões na árvore.
Árvore passiva: 60 nós compartilhados, com 3 entradas (uma por classe). Nós grandes mudam regras ("Bloquear gera 1 carga de Ímpeto"); nós pequenos dão números.
Respec: grátis até o nível 10; depois custa Ouro, sempre com o preço mostrado antes.

### Livros e Sigilos
Livro de Conhecimento ensina uma habilidade (rank 1). Livros repetidos viram Páginas; Páginas sobem a habilidade até o rank 3 no Acesso Antecipado.
Sigilo de Suporte é um item que encaixa numa habilidade e a modifica (+projétil, +área, repetir golpe). Remove e recoloca sem custo. Slots: 1 no nível 5, 2 no nível 15, 3 no nível 25.
Proteção contra azar: todo livro básico também pode ser comprado da Irmã Odete depois de visto uma vez. Nenhuma build depende de sorte para existir.

### Raridades no Acesso Antecipado

Raridade

Estrutura

Papel

Comum

Base + propriedade da base

Material de crafting, item inicial

Mágico

Até 2 afixos

Progressão rápida na campanha

Raro

Até 4 afixos

Coluna da build

Único

Atributos fixos + 1 efeito que muda a build + 1 contrapartida

Item de desejo, caçado em chefes

### De onde vem cada coisa

Recompensa

Jogo manual

Expedição idle

Comum e Mágico

Sim

Sim

Raro

Sim

Sim, com chance reduzida e no máximo 4 por expedição

Único

Sim (chefes e elites)

Nunca

Livro de habilidade básica

Sim

Só Páginas, nunca livro inteiro

Livro de especialização

Sim (chefes)

Nunca

Sigilo de Suporte

Sim

Só Sigilos comuns

Materiais e Ouro

Sim

Sim (principal fonte do idle)

Entradas de mapa endgame

Sim

Nunca

### Crafting com o Bram

Operação

Entrada

Resultado

Refinar

Item Comum + Lascas

Vira Mágico com afixos aleatórios

Reforjar

Item Mágico ou Raro + Cinzas de Memória

Sorteia todos os afixos de novo

Fixar Inscrição

Item Raro + Inscrição

Adiciona 1 afixo escolhido de uma lista curta (1 por item)

Lapidar

Item + Ouro

Melhora os valores de um afixo dentro da faixa dele

Reciclar

Qualquer item

Devolve Lascas e Cinzas
Crafting nunca destrói o item. O risco é perder uma combinação boa, e a tela avisa antes. A principal saída de Ouro é Lapidar, respec e comprar livros: o idle gera Ouro, e o Ouro vira poder só por crafting e escolhas.

## 7. Expedições idle: regras rígidas
O idle é um complemento, nunca um substituto. A patrulha rende a taxa base, e jogar na mão ativa o Fervor do Recuperador, que triplica o XP e é a única fonte de itens de topo. As expedições também dependem de Cargas do Marco, que só se ganham jogando. Os números são os mesmos de um "idle com penalidade", mas o jogador sente que é recompensado por jogar, não castigado por usar o idle.

### As 8 regras
Só território dominado. Uma expedição só roda em áreas que o personagem venceu na mão, do início ao fim, incluindo o chefe. No endgame, só até 1 tier abaixo do maior tier vencido manualmente.
Fervor do Recuperador. A patrulha rende a taxa base de XP. Jogar na mão ativa o Fervor: XP ×3, Ouro e materiais ×1,25, chance de Raro ×2 e acesso a Únicos e Fragmentos de Eco. Na prática, o idle rende cerca de 35% do XP por hora do jogo manual.
Teto de nível. O XP do idle para de entrar quando o personagem passa 2 níveis acima da área farmada. Para subir mais, é preciso conquistar áreas novas jogando.
Sem itens de topo. Únicos, livros de especialização, Sigilos raros e entradas de mapa nunca caem no idle. Raros caem com metade da chance e no máximo 4 por expedição.
Cargas do Marco. Cada hora de expedição gasta 1 carga (máximo de 12 guardadas). Cargas se ganham jogando: limpar uma área na mão dá +1, vencer um chefe dá +2, conquistar uma área nova dá +3. Para o jogador ocupado não ficar zerado, o descanso dá +4 cargas por dia real, sem acumular.
Vigor da patrulha. O personagem sai descansado: as primeiras 4 h rendem 100% da taxa da patrulha; depois ele cansa (70% nas horas 5–8, 40% nas horas 9–12). Duas expedições curtas valem mais que uma longa, o que incentiva voltar ao jogo.
Um personagem por vez. Só um personagem do save pode estar em expedição. Um segundo slot vira recompensa de endgame, nunca compra.
Risco real. A build e as regras de IA ficam congeladas no início. Falta de resistência, de mana ou de poções faz o personagem recuar mais cedo. O loot já obtido nunca é perdido.

### Manual contra idle na mesma área

Medida (por hora, mesma área)

Patrulha (idle)

Jogo manual com Fervor

XP

Taxa base (cai após a 4ª hora)

×3

Ouro e materiais

Taxa base

×1,25

Chance de Raro

Taxa base, máximo 4 por expedição

×2, sem limite

Únicos e livros de especialização

Não

Sim

Fragmentos de Eco

Não

Sim

Cargas do Marco

Gasta

Gera

Conquistas da Steam

Só as de expedição

Todas as outras
Fragmentos de Eco caem só de elites e chefes no jogo manual. Com 50 fragmentos, o jogador escolhe um Único já visto no Codex e o fabrica. É a proteção contra azar, e ela recompensa só quem joga.

### Como apresentar: bônus, não castigo
Nunca mostrar números negativos como "-65% de XP". A patrulha é a taxa normal; no jogo manual, o HUD mostra o ícone do Fervor e "+200% XP".
O relatório da expedição termina com um convite: "Jogando esta rota você teria Fervor e chance de Únicos", com um botão "Jogar esta rota agora".
Os limites são explicados pela história: a patrulha "repete o caminho, não descobre nada novo"; os Únicos "só respondem a um Recuperador presente".
O cansaço aparece como barra de Vigor do personagem, uma coisa natural, não como penalidade do sistema.
Ganhar Fragmentos de Eco tem som e efeito próprios, para o jogador associar "jogar na mão" a "progresso especial".

### E os bots?
Como o jogo é offline e single-player, um bot só "rouba" do próprio jogador, e não há economia de outros jogadores para estragar. Mesmo assim, por design:
O idle não abre conteúdo novo, então automatizar só serve para farmar o que já foi vencido.
Chefes têm padrões com variação e exigem reação, o que deixa um macro simples inútil.
Se houver rankings no futuro, só contam corridas manuais com replay validado (decisão para o 1.0).
Se o relógio do PC voltar no tempo durante uma expedição, ela encerra com o loot já contado e sem recompensa extra.

### Como a expedição funciona
No Refúgio, falar com a Ilsa e escolher uma área dominada e um objetivo (XP, Ouro ou Materiais).
Configurar as regras de IA: até 6 regras em ordem, por exemplo "poção abaixo de 35% de vida" ou "Fenda de Pedra se houver 3 ou mais inimigos".
Escolher a duração (1–12 h, limitada pelas cargas). A tela mostra uma previsão em faixa: "8–12 mil de XP, risco de recuo médio por falta de resistência a fogo".
Fechar o jogo. Ao abrir, o jogo simula os encontros no tempo que passou (com teto de 12 h) usando o mesmo motor de regras do combate.
O Tico entrega o relatório: tempo efetivo, encontros vencidos, poções gastas, motivo da parada e loot, com uma dica ("sua cura falhou 3 vezes; tente subir o limiar para 45%").

## 8. Endgame inicial
Depois do Vigia do Sino abre a Carta dos Marcos: 3 mapas repetíveis em 5 tiers, que levam o personagem do nível 15 ao 30 e terminam num chefe de endgame. O endgame é pequeno de propósito; ele cresce a cada atualização do Acesso Antecipado.

### Mapas

Mapa

Ambiente

Inimigos predominantes

O que favorece

Ossário do Marco

Cripta profunda

Ecos de soldado e elites com escudo

Builds de alvo único e quebra de guarda

Trilha de Cinza

Floresta morta

Fauna alterada rápida, atiradores

Mobilidade e dano em área à distância

Salão do Martelo

Oficina abandonada

Constructos com armadura

Dano elemental e controle

### Tiers e entradas
Tiers 1–5, níveis de monstro 16, 19, 22, 25 e 28.
Pedras de Rota abrem um mapa num tier. Caem só no jogo manual, em mapas do tier anterior ou de chefes. Vencer o tier N na mão libera o tier N+1 e o idle no tier N−1.
Modificadores: cada Pedra de Rota vem com 0 a 3 modificadores, como "inimigos com escudo", "menos regeneração de mana" ou "elites explodem ao morrer". Cada modificador aumenta a quantidade de loot em 15%. Sempre visíveis antes de entrar.

### Chefe de endgame: Predador dos Marcos
Uma fera feita de memórias de caça que vaga entre os três mapas. Rastros aparecem aleatoriamente nos mapas de tier 3 ou mais. Juntar 3 rastros abre a arena. A luta alterna entre caçar o jogador, sumir na névoa e investidas telegrafadas. Drop garantido de 1 Único da sua tabela própria e 10 Fragmentos de Eco.

### Por que continuar jogando depois do nível 30
Caçar os 12 Únicos e completar o Codex.
Testar especializações e classes novas no mesmo save (baú compartilhado acelera o segundo personagem).
Desafios semanais offline: uma seed fixa de mapa com modificadores, igual para todos, e conquista da Steam por completar.
Atualizações de conteúdo: Assassino, Necromante e Ato II.

## 9. Arte, áudio e uso de IA

> **Substituído em 16/10/2026:** a direção visual e as especificações de arte desta seção valem só como histórico. O que vale está em `docs/arte/03_design_system.md` e `docs/arte/referencias-geracao/`. A regra de declarar à Steam o uso de IA continua valendo.
A direção visual do plano 1.1 continua (pixel art oblíqua em ocre, carmesim, dourado e preto carvão), mas os assets finais são feitos ou refeitos à mão. Qualquer conteúdo gerado por IA que entre no jogo ou na página da Steam precisa ser declarado no questionário de conteúdo da Steam.

### Especificações de arte

Item

Padrão

Personagens jogáveis

64 × 96 px (escala da referência), 4 direções + espelhamento no demo, 8 direções no Acesso Antecipado

Inimigos comuns

48 × 72 px; chefes de 128 a 256 px

Tiles

64 × 32 px (isométrico 2:1)

Ícones

32 × 32 px

Resolução interna

960 × 540, escalada ×2 para 1080p e ×4 para 4K (1440p com barras ou escala suave)

Paleta

Carvão #16130F · Ocre #9B713E · Dourado #C7963C · Carmesim #8C2326 · Perigo #D74437 · Pergaminho #EAD9B5

### Animações por classe (mínimo)
Parado, andar, esquiva, ataque básico, 2 animações de habilidade reaproveitáveis (golpe e conjuração), tomar dano e morte. Habilidades diferentes reaproveitam essas animações com efeitos visuais próprios. Isso corta o custo de arte pela metade.

### Áudio
Música: 6 faixas no Acesso Antecipado (Refúgio, Estrada, Cripta, Pedreira e Túneis, chefe, endgame). Instrumentos acústicos com percussão grave e um sino como tema recorrente.
Efeitos: biblioteca comprada (licença comercial) + sons próprios para os momentos-chave: drop de Único, sino, expedição concluída.
Voz: sem dublagem no Acesso Antecipado; só "grunhidos" e exclamações curtas.

### Política de IA

Uso

Permitido?

Observação

Arte conceitual e exploração de ideias

Sim

Uso interno

Sprites, tiles e ícones finais

Não (feitos por artista)

Garante consistência e evita problema de direitos

Capa e cápsulas da Steam

De preferência não

Se usar, declarar na Steam

Textos e diálogos

Rascunho sim; final revisado por humano

Declarar se o texto final for gerado

Código

Sim

Não precisa declarar

### Orçamento de arte
O maior custo do projeto. Opções: (a) aprender pixel art e fazer tudo, mais lento; (b) contratar um pixel artist freelancer por pacote (ex.: 1 classe completa, 1 bioma, 1 chefe); (c) assets comprados (itch.io, por exemplo) só para protótipo, trocados antes do demo público.

### Galeria: artes conceituais (do plano 1.1)
Estas quatro imagens vêm do PDF original e definem o clima: ocre, carmesim e dourado sobre preto. São conceitos, não sprites do jogo, e parecem geradas por IA; servem como referência interna e não devem ir para a página da Steam sem ser refeitas ou declaradas.

Capa. O Recuperador olha para as torres flutuantes do Arquivo Vivo. Boa base para a cápsula principal da Steam: personagem de costas, título no céu escuro.

Cripta Partida. Mostra a câmera oblíqua, a escala do Guardião e o telegraph em cone vermelho do martelo: exatamente a leitura de perigo que a seção 5 pede.

Classes. Da esquerda para a direita: Guerreiro, Caçadora (vira o Arqueiro), Arcanista (vira o Mago), Assassino e Necromante. Os três primeiros são o elenco do Acesso Antecipado.

Itens. Doze famílias de equipamento. Serve como guia de silhueta para os ícones de 32 × 32.

### Referência de estilo oficial
Esta imagem é o alvo visual do jogo: câmera isométrica 3/4, pixel art detalhado, iluminação dramática e interface ornamentada com dourado. Ela parece gerada por IA (textos ilegíveis, "USDC" da versão antiga), então serve como alvo de estilo, não como asset do jogo.

### Leitura da referência, elemento por elemento

#

Elemento

Manter

Mudar

1

Retrato e barras

Retrato da classe com moldura, barras finas

O recurso muda por classe: Ímpeto, Foco ou Mana

2

Faixa do título

Fonte serifada clara sobre faixa escura

Mostrar o nome da área ("Cripta Partida"), não o do jogo

3

Moeda

Ícone com contador no canto

Trocar USDC por Ouro e Cargas do Marco

4

Minimapa

Isométrico, no canto superior direito

Nada

5

Painel de build

Resumo lateral

Abre e fecha com uma tecla; textos reais

6

Telegraph

Cone laranja com grade e brasas no chão

Manter igual: vira o padrão de todo ataque de chefe

7

Chefe

Golem mecânico com núcleo de fogo

Encaixa como chefe do Salão do Martelo (endgame)

8

Jogador

Silhueta clara, capa carmesim, arma grande

Ótimo exemplo de Guerreiro Ruptor

9

Feixes de loot

Coluna de luz + nome + raridade

Cor do feixe por raridade; nomes reais do jogo

10

Barra inferior

Vida e recurso, habilidades, poções, moldura ornamentada

6 habilidades + esquiva + 2 poções; "Health" vira "Vida"

11

Segundo minimapa

Nada

Remover (duplicado)

12

Cenário

Gelo, canos, neblina, colunas cobertas de neve

Vira um bioma gelado (endgame ou Ato II); o Ato I continua ocre

### Paleta da referência

A referência segue uma regra que vale para todos os biomas: base fria e escura, acentos quentes só onde importa (perigo, loot, fogo, vida). No Ato I a base troca para ocre e pedra quente, mas os acentos e a interface dourada continuam os mesmos, para o jogo parecer um só.

### Briefing de arte
Para um pixel artist ou para uma ferramenta de IA de imagem (o prompt em inglês costuma funcionar melhor):
Pedir sem texto: IA gera letras ilegíveis. Textos e números entram depois, com a fonte do jogo.
Para o artista, enviar junto: esta referência, a tabela acima, as especificações de sprite desta seção e uma classe por vez (começar pelo Guerreiro).
Esse nível de detalhe custa bem mais por sprite que pixel art simples. Pedir orçamento de 1 personagem completo antes de fechar o pacote todo.

## 10. Tecnologia e arquitetura
O jogo roda 100% local em Godot 4, com GDScript tipado, sem servidor. A regra que guia toda a arquitetura: um único motor de regras, sem depender de cenas, usado tanto pelo combate em tempo real quanto pelo simulador do idle. Se as duas partes calcularem dano de formas diferentes, o idle vira outro jogo.

### Decisões de base

Tema

Decisão

Por quê

Motor

Godot 4.x, última versão estável no início da F1, fixada até o Acesso Antecipado

Atualizar o motor no meio do projeto quebra coisas; só atualizar entre fases, com testes passando

Linguagem

GDScript com tipagem estática em tudo (var dano: float)

Integração total com o editor, iteração rápida; a tipagem pega erros cedo e deixa o código mais rápido

Renderização

Renderer Compatibility (OpenGL)

Pixel art 2D não precisa do Forward+; roda em PCs fracos e notebooks

Resolução

Viewport interno 960 × 540, stretch mode viewport, escala inteira, filtro nearest

Pixels nítidos em 1080p (×2) e 4K (×4); comporta o nível de detalhe da referência

Entrada

Só teclado e mouse no Acesso Antecipado, mas tudo via InputMap (ações nomeadas)

Adicionar controle no 1.0 vira só mapear ações, sem mexer na lógica

Steam

Plugin GodotSteam (GDExtension)

Conquistas, Cloud, Rich Presence e overlay

Versionamento

Git + GitHub, com Git LFS para arquivos de arte e áudio

Histórico seguro; LFS evita repo gigante

### Princípios
Dados fora do código. Nenhum número de balanceamento dentro de script. Tudo em Resources ou tabelas.
Lógica separada da apresentação. Regras são classes RefCounted puras; cenas (Node) só desenham, tocam som e leem input.
Determinismo. Mesma seed + mesmos dados + mesmo snapshot = mesmo resultado, sempre. Isso torna o idle testável e os bugs reproduzíveis.
Comunicação por sinais e eventos. Sistemas não se chamam diretamente; um barramento de eventos (EventBus) avisa "inimigo morreu", "item caiu", "expedição terminou".
Offline primeiro, sem confiança no relógio. O jogo nunca depende de internet; o relógio do PC é tratado como entrada que pode estar errada.

### Estrutura de pastas

### Arquitetura
Os dados alimentam um único motor de regras; a interface, o combate e o simulador só consultam esse motor, e o teste de paridade garante que combate e simulador cheguem aos mesmos resultados.

### Dados de conteúdo
Resources tipados para cada tipo de conteúdo: ClassData, SkillData, ItemBaseData, AffixData, EnemyData, MapData, LootTableData.
Balanceamento em planilha: as tabelas numéricas (afixos, curvas de XP, tabelas de loot) ficam numa planilha exportada para CSV. Um script de importação (tools/import_tables.gd) converte o CSV em .tres e valida tudo: IDs únicos, referências existentes, faixas mínimas menores que as máximas, pesos de loot maiores que zero. Se algo falhar, o build falha.
IDs estáveis em texto (skill.warrior.iron_cut, affix.life_flat), nunca renomeados depois de publicados. O save guarda IDs, não caminhos de arquivo.
Versão de conteúdo: um número content_version salvo junto com cada expedição e cada save.

### Sistema de atributos e modificadores
Todo atributo (vida, dano físico, velocidade de ataque, resistência a fogo...) é calculado pela mesma fórmula, com três tipos de modificador:
Plano (+10 de vida): soma direto na base.
Aumentado (+20% de dano físico): todos somam entre si antes de multiplicar. É o tipo mais comum em afixos.
Mais (20% mais dano): cada um multiplica separado. Raro; usado em Sigilos, Únicos e nós grandes da árvore.
Tags decidem quais modificadores valem para cada habilidade: ataque, feitiço, corpo_a_corpo, projétil, área, fogo, frio, raio, físico. "+15% de dano de projétil" só entra em habilidades com a tag projétil.
O resultado fica em cache e só é recalculado quando algo muda (trocar item, subir nível, ganhar ou perder um efeito).

### Ordem de cálculo de um golpe
Dano base da habilidade (ou da arma, se a habilidade escala com arma) × coeficiente da habilidade.
Modificadores planos, aumentados e "mais" que batem com as tags.
Crítico: rolagem com a seed do combate; multiplicador base 150%.
Defesa do alvo, nesta ordem: evasão (só ataques; teto 70%) → bloqueio (teto 50%) → armadura (só físico) → resistência elemental (teto 75%) → barreira → vida.
Efeitos ao acertar: queimadura, lentidão, quebra de guarda, ganho de Ímpeto.
Armadura reduz menos os golpes grandes que os pequenos, o que incentiva esquivar dos ataques fortes de chefe:

### Efeitos e limites
Cada efeito (queimadura, lentidão, marca, barreira) é um EffectData com duração, intervalo de tick e regra de acúmulo: renovar, acumular até N, ou só o mais forte vale.
Todo efeito que dispara sozinho ("ao bloquear", "ao matar") tem recarga interna mínima de 0,25 s e não pode disparar outro efeito do mesmo tipo. Isso impede laços infinitos.
Nenhum valor final pode ficar negativo; custos têm mínimo de 0 e recargas têm mínimo de 0,1 s.

### Combate em tempo real
Física a 60 Hz e lógica de combate no _physics_process, independente do FPS.
Habilidade = dados + comportamento: SkillData guarda custo, recarga, tempos de preparação, impacto e recuperação, tags e coeficientes. Um script pequeno de comportamento define a forma (cone, projétil, área, avanço). O cálculo de dano sempre passa pelo motor de regras.
Acerto com Area2D e consultas de forma; cada golpe acerta o mesmo alvo no máximo uma vez, salvo regra explícita.
IA dos inimigos com máquina de estados simples: parado → perseguir → telegraph → atacar → recuperar. Chefes usam a mesma base, com uma tabela de padrões por fase.
Hitstop por entidade (pausa curta só de quem bateu e de quem apanhou), nunca congelando o jogo todo.
Pools de objetos para projéteis, números de dano, partículas e itens no chão.

### Simulador de expedição
O simulador resolve a expedição encontro por encontro, sem posições nem física, usando o mesmo motor de regras do combate.
Encontros em dados: cada mapa tem uma lista de EncounterTemplate (grupo de inimigos, densidade, tempo de travessia até o próximo grupo).
Passos de 0,1 s: a cada passo, a política do jogador escolhe a primeira regra válida ("poção abaixo de 35%", "Fenda de Pedra com 3 ou mais inimigos", senão ataque básico). Os inimigos atacam conforme seus dados.
Perfil idle por habilidade (IdleProfile): traduz o que é espacial em números. Por exemplo: quantos inimigos do grupo a Fenda de Pedra acerta em média, quanto tempo o Guerreiro gasta para alcançar atiradores, que fração dos ataques telegrafados a IA consegue esquivar (base de 50%, pior que um bom jogador). Esses valores são calibrados pelo teste de paridade, não chutados.
Recibo por encontro: resultado, duração, poções gastas, XP e loot. O total da expedição é a soma dos recibos, com as taxas da seção 7 aplicadas uma única vez.
RNG em fluxos separados: combate, loot e eventos usam geradores diferentes, cada um com seed derivada de hash(seed_expedição, fluxo, índice_do_encontro). Assim, simular em uma vez ou em 10 partes dá exatamente o mesmo resultado, e mudar um detalhe do combate não muda o loot.
Desempenho: 12 h são cerca de 720 encontros e 200 mil passos. Rodar numa thread (WorkerThreadPool) enquanto a tela mostra "o Tico está voltando..."; meta de menos de 2 s num PC modesto. Se passar disso, aumentar o passo para 0,25 s nos encontros sem chefe.
Incompatibilidade explícita: habilidade ou Único sem IdleProfile testado bloqueia a expedição com uma mensagem clara ("Raio do Arquivo ainda não funciona em patrulha"). Nunca inventar um equivalente genérico.

### Teste de paridade (combate × simulador)
O maior risco técnico é o combate e o simulador se afastarem com o tempo. A solução é um teste automático:
Um bot de teste joga as cenas reais em modo headless (sem janela), com a mesma política de regras da expedição e seeds fixas, em 200 encontros por build e mapa.
O simulador roda os mesmos encontros com as mesmas seeds.
Compara XP por minuto, abates por minuto, dano recebido e poções por encontro. Tolerância inicial de 10%, a apertar para 5% no Acesso Antecipado.
Se falhar, o build falha. Uma ferramenta sugere novos valores de IdleProfile a partir da diferença medida.
Roda toda noite no CI e antes de qualquer versão publicada.

### Relógio e tempo offline
Sempre UTC: início da expedição salvo como horário Unix (Time.get_unix_time_from_system()). Fuso e horário de verão não importam, e a expedição funciona igual se o save abrir em outro PC pelo Steam Cloud.
Conferência com a Steam: quando houver conexão, comparar com o horário do servidor da Steam (getServerRealTime no GodotSteam). Se a diferença passar de 10 min, usar o horário da Steam.
Relógio voltando: o save guarda last_seen a cada salvamento. Se agora < last_seen − 5 min, a expedição é encerrada no último ponto conhecido, sem tempo extra.
Relógio adiantado: limitado pela duração escolhida e pelo teto de 12 h. Adiantar o relógio só adianta o que o jogador já ia receber, sem multiplicar nada.

### Save
Formato: JSON legível, fácil de migrar e de depurar. Um arquivo por slot de save (slot_1.json) e um arquivo separado para configurações.
Conteúdo: save_version, content_version, personagens, baú compartilhado, domínios, Cargas do Marco, last_seen e a expedição em andamento (snapshot, seed, início, duração, status).
Gravação segura: escrever em slot_1.tmp, conferir, e só então renomear para slot_1.json. Manter 3 backups rotativos e um checksum (SHA-256) no arquivo. Se o save principal estiver corrompido, carregar o backup mais recente e avisar o jogador.
Quando salvar: ao trocar de área, ao coletar uma expedição, ao crafting, ao sair e a cada 5 min.
Coleta sem duplicar: o status da expedição muda para coletada no mesmo salvamento que adiciona o loot. Se o jogo fechar no meio, ao reabrir o simulador recalcula o mesmo resultado (é determinístico) e entrega uma única vez.
Migrações: cada mudança de formato ganha uma função migrar_de_N_para_N+1. O CI guarda um save de exemplo de cada versão publicada e testa se todos carregam na versão nova. Isso evita o pior tipo de avaliação negativa no Acesso Antecipado: "a atualização apagou meu progresso".
Pasta própria: ativar use_custom_user_dir no projeto, para o save ficar em %APPDATA%/EchoesOfTheShatter e não numa pasta genérica do Godot.

### Steam Cloud
Usar o Auto-Cloud da Steam (configurado no Steamworks, apontando para a pasta de saves). Configurações gráficas ficam fora da nuvem, porque cada PC tem a sua.
Em conflito entre dois PCs, a Steam pergunta qual versão manter; o menu do jogo também mostra data, nível e tempo de jogo de cada slot para ajudar na escolha.

### Localização
Nenhum texto fixo no código: tudo via chave e tr() (ui.inventory.title, skill.warrior.iron_cut.name). Um CSV com colunas chave, pt_BR, en, es vira tradução no Godot.
Nomes de itens gerados com gênero: em português e espanhol, "Espada Flamejante" e "Machado Flamejante" funcionam, mas "Lança Sombrio" não. Cada base guarda o gênero, e cada afixo tem forma masculina e feminina. Nunca montar frases concatenando pedaços.
Fonte pixel com acentos: testar ç, ã, õ, á, ñ, ¿ desde o início; trocar de fonte depois quebra a interface toda.
Espaço na interface: português e espanhol ocupam cerca de 30% mais espaço que inglês. Desenhar a interface com o texto mais longo.

### Entrada (só teclado e mouse no Acesso Antecipado)

Ação

Tecla padrão

Mover

WASD

Mirar

Mouse

Ataque básico

Botão esquerdo

Habilidades 1–5

Botão direito, Q, E, R, F

Esquiva

Espaço

Poções

1 e 2

Inventário, árvore, mapa

I, P, M
Todas as teclas remapeáveis desde o demo, com a configuração salva.
Tudo passa por ações do InputMap, nunca por tecla fixa no código. Quando o controle entrar no 1.0, basta mapear as ações e adaptar as telas de menu.

### Testes automáticos

Tipo

O que cobre

Quando roda

Unitários (GUT)

Fórmulas de atributos, ordem de cálculo, tetos, efeitos, regras de acúmulo

A cada commit

Dados

Validador das tabelas: IDs, referências, faixas, pesos

A cada commit

Loot estatístico

1 milhão de sorteios por tabela; a frequência observada bate com o peso esperado; nada fora do tier cai

A cada commit (versão rápida) e toda noite (completa)

Regras do idle

Nenhum Único, livro de especialização ou entrada de mapa sai do idle; tetos de XP, Raros e cargas respeitados

A cada commit

Determinismo

Mesma seed simulada em 1 parte e em 10 partes dá resultado idêntico

A cada commit

Paridade

Combate real × simulador (seção acima)

Toda noite e antes de publicar

Saves

Saves de exemplo de todas as versões publicadas carregam e migram

A cada commit

Fumaça

Abre o jogo headless, carrega o Refúgio e a Cripta, roda 60 s de bot

Antes de publicar

### CI e builds na Steam
GitHub Actions com Godot headless: roda os testes, exporta o build Windows e guarda o artefato.
SteamPipe via steamcmd no CI: um push na branch release sobe o build para a branch beta da Steam; promover para default é sempre manual, no painel do Steamworks.
Branches da Steam: default (público), beta (opt-in para a comunidade), playtest (com senha, para testadores do Discord).
Demo como app separado (a Steam trata demo como um AppID próprio), gerado do mesmo projeto com uma flag que limita o conteúdo à Estrada e à Cripta.
Versão visível no canto do menu (0.3.1-ea+a1b2c3) para relatórios de bug.

### Orçamento de desempenho

Medida

Meta

FPS

60 estáveis em PC de entrada (GPU integrada, 8 GB de RAM)

Inimigos na tela

Até 80 com 60 FPS; acima disso, inimigos fora da tela com IA simplificada

Projéteis e partículas

Pools pré-alocados; limite de 300 projéteis ativos

Carregamento de área

Menos de 3 s

Simulação de 12 h de idle

Menos de 2 s

Tamanho do build

Menos de 500 MB

### Erros, logs e telemetria
Relatório de erro: Sentry (tem SDK para Godot) para capturar travamentos com versão e pilha de chamadas, mas só com permissão do jogador no primeiro uso.
Log local rotativo em user://logs; o menu tem um botão "abrir pasta de logs" para enviar no Discord.
Telemetria de playtest (opt-in): nos builds de demo e beta, enviar eventos anônimos (tempo até vencer o Guardião, mortes por chefe, tempo manual × idle). Sem nome, e-mail, IP ou ID da Steam, sem uso comercial e sem perfilamento, para cumprir a LGPD e o ECA Digital (seção 13). Isso alimenta as métricas da seção 12.

### Ferramentas de desenvolvimento
Console de debug (só em build de desenvolvimento): dar item, teleportar, subir nível, ligar invencibilidade, mostrar hitboxes.
Acelerador de tempo: 1 h de expedição = 10 s.
Simulador em lote (tools/batch_sim.gd): roda 10 mil expedições por build e exporta CSV com XP, Ouro, Raros e motivo de parada, para balancear na planilha.

## 11. Roadmap
A estimativa é de 13 a 18 meses até o Acesso Antecipado para uma equipe de 1 a 2 pessoas, mas o número real só aparece depois da F1: medir quanto tempo o protótipo levou e recalcular. Nenhuma fase começa antes de o portão da anterior ser cumprido.
A F3 é a fase decisiva: o demo no Steam Next Fest diz se vale a pena investir os 6 a 9 meses da F4.

### Marcos da Steam
Pagar a taxa do Steam Direct (US$ 100 por jogo, recuperável após US$ 1.000 em vendas) e montar a conta de desenvolvedor no começo da F3
Página "Em breve" no ar no início da F3, com GIFs do combate e da tela de expedição
Trailer de 60–90 s mostrando o gancho: luta → domínio → expedição → relatório → chefe
Demo inscrito em um Steam Next Fest (edições em fevereiro, junho e outubro)
Postar o progresso em r/ARPG, r/incremental_games, r/godot e TikTok/Shorts desde a F1
Contatar criadores de conteúdo de ARPG e idle no Brasil e fora antes do Next Fest
Lançamento do Acesso Antecipado com desconto de lançamento de 10–15%

## 12. Riscos, métricas e decisões em aberto
Os dois maiores riscos são o combate não ficar divertido e a arte custar mais do que o projeto aguenta; os dois são testados cedo, na F1 e na F3.

### Riscos

Risco

Sinal de alerta

Resposta

Combate sem graça

Testadores param de jogar antes do Guardião

Não avançar da F1; iterar o checklist de impacto

Idle vira muleta

Jogadores com mais tempo em idle do que em manual após a 1ª semana

Apertar cargas e XP (seção 7); os números são configuráveis em dados

Idle fraco demais (ninguém usa)

Menos de 30% dos jogadores iniciam a 2ª expedição

Melhorar o relatório e a recompensa de Ouro e materiais, sem liberar Únicos

Arte cara ou inconsistente

Sprites de pessoas diferentes não combinam

Guia de estilo fechado na F3; um único artista principal

Escopo cresce

Vontade de adicionar a 4ª classe antes do Acesso Antecipado

Esta matriz de conteúdo é o contrato; ideias novas vão para o backlog do 1.0

Poucas wishlists

Menos de 2 mil antes do Next Fest

Mudar cápsula, trailer e gancho antes de seguir para a F4

Nome difícil fora do Brasil

Jogadores estrangeiros não lembram o nome

Resolvido: Echoes of the Shatter como nome principal

### Métricas do demo e do Acesso Antecipado
Tempo até vencer o Guardião e quantas tentativas leva.
Porcentagem de jogadores que iniciam a 1ª expedição e que voltam para coletar.
Razão manual/idle de tempo de jogo por semana. Meta: manual ≥ 60% do tempo ativo.
Build mais usada por classe: nenhuma acima de 50%.
Mediana de tempo jogado no demo (referência saudável: 20 min ou mais).
Wishlists por semana e conversão de wishlist em venda no lançamento.
Avaliações da Steam: meta de "Muito positivas" (80%+).

### Decisões em aberto
Registrar a marca Echoes of the Shatter (INPI e USPTO) e reservar domínio e perfis nas redes sociais
Arqueiro com escolha de gênero ou personagem fixo (vale para as 3 classes)
Fazer a arte você mesmo, contratar freelancer ou um misto
Valores finais das regras do idle (35% de XP, cargas, teto de nível), a calibrar no playtest da F2
Preço final do Acesso Antecipado
Coop no 1.0 ou nunca (exigiria servidor ou P2P e muda a arquitetura)
Equipe: sozinho ou com parceiros (programação, arte, áudio)

## 13. Marco legal e conformidade
O plano v2.0 já está alinhado com a lei brasileira: o jogo não tem loot box paga, não tem compra dentro do jogo, não tem chat e não dá prêmio com valor real. Os pontos que exigem ação são três: o questionário de classificação indicativa na Steam, a política de privacidade da telemetria e os cuidados extras se um dia houver coop ou compras. Esta seção é um resumo técnico, não parecer jurídico; antes do lançamento, vale uma revisão com advogado de games.

### As três normas que se aplicam

Norma

O que é

Ponto central para o jogo

Lei 14.852/2024 (Marco Legal dos Games)

Define jogo eletrônico, garante liberdade para desenvolver e cria incentivos

Sem autorização prévia do governo (art. 3º); jogos com apostas, prêmios em ativos reais ou virtuais ou resultado aleatório de aposta ficam fora da lei e dos benefícios (art. 5º, parágrafo único)

Lei 15.211/2025 (ECA Digital), em vigor desde 17/03/2026

Proteção de crianças e adolescentes em serviços digitais

Proíbe loot boxes pagas em jogos para menores ou de acesso provável por eles, conforme a classificação indicativa (art. 20); interação entre usuários limitada por padrão (art. 21); privacidade desde a concepção; proibido perfilamento comportamental de menores para fins comerciais

Classificação indicativa (Portaria MJSP 1.048/2025)

Faixa etária obrigatória, agora considerando interatividade

Na Steam, sai de um questionário gratuito no Steamworks; sem ela, a página fica invisível para usuários no Brasil

### Como cada decisão do plano se encaixa

Decisão do plano

Situação legal

Ação

Sem Solana, NFT ou USDC

Essencial. Com prêmios em ativos reais, o jogo provavelmente cairia na exclusão do art. 5º e perderia acesso a fomento, além de ser proibido na Steam

Nenhuma; manter descartado

Drops aleatórios de itens

Permitido. Loot box, pelo ECA Digital (art. 2º, IV), exige pagamento; drop ganho jogando não é loot box

Nunca vender baús, chaves ou sorteios por dinheiro real, nem no futuro

Preço fechado, sem microtransações

Ideal. A classificação deve considerar riscos de microtransações (art. 3º, §2º), e compras para menores precisam vir bloqueadas por padrão (art. 17)

DLC ou pacote de apoiador só pela loja da Steam, que já tem controle parental

Single-player, sem chat

Fora das obrigações pesadas de moderação (art. 16 do Marco Legal, art. 21 do ECA Digital)

Se o coop entrar no 1.0: canal de denúncia, bloqueio, interação desligada por padrão e controle parental

Fantasia sombria com violência

A classificação provável fica entre 12 e 16 anos; isso torna o jogo "de acesso provável" por adolescentes

Manter a opção de reduzir sangue e flashes; responder o questionário com honestidade

Telemetria e relatório de erros

Sujeitos à LGPD e, para adolescentes, à proibição de perfilamento comercial do ECA Digital

Opt-in, anônima, sem IP armazenado, sem uso comercial; política de privacidade em português simples

Acessibilidade (texto escalável, remapeamento, redução de flashes)

O Marco Legal pede acessibilidade para crianças com deficiência (art. 15, §3º)

Já previsto; manter no checklist de cada fase

### Fomento: dinheiro que o Marco Legal abre
O Marco Legal tornou os jogos um segmento cultural, e o decreto que o regulamenta ("Desenvolve Gamers Brasil") foi assinado em 14/10/2026. Empresas com receita de até R$ 16 milhões por ano têm tratamento especial de fomento (art. 8º), o que inclui um estúdio indie.

Fonte

Como funciona

Encaixe no Echoes of the Shatter

Lei Rouanet (arts. 12 e 18)

Projeto aprovado pelo MinC capta patrocínio de empresas, que abatem do IR; o programa Rouanet Games oferece cursos para preparar projetos

Bom para a F4 (produção do Acesso Antecipado). Exige CNPJ e projeto bem escrito; captar patrocínio é a parte difícil

Lei do Audiovisual (art. 11)

Incentivos de investimento via Ancine

Alternativa à Rouanet; mesmo perfil de exigência

FSA (Fundo Setorial do Audiovisual)

Empréstimo com juros, não doação; R$ 460 milhões em 2026 para todo o audiovisual. Há proposta de baixar o mínimo de R$ 500 mil para R$ 150 mil, ainda pendente

Só faz sentido com equipe e orçamento maiores; acompanhar se o mínimo cair

Finep

Chamada de R$ 200 milhões para startups de jogos

Vale acompanhar a partir da F3, com demo e página na Steam para mostrar

Editais estaduais e municipais de cultura

Prêmios e apoios a projetos culturais, que agora podem incluir jogos

Muitas vezes são o caminho mais acessível para indie; pesquisar os do seu estado e município
Regra prática: fomento leva meses entre edital, aprovação e pagamento. Não colocar dinheiro de edital no caminho crítico do roadmap; tratar como acelerador.

### Empresa e registros
Formato da empresa: o Marco Legal permite que profissionais de jogos se formalizem como MEI, microempresa ou empresa de pequeno porte, no Simples Nacional, quando aplicável (art. 7º, §2º). A lei mandou o IBGE criar uma CNAE própria para desenvolvimento de jogos (art. 7º, §4º); confirmar com o contador se ela já existe e qual se encaixa.
CNPJ ajuda em tudo: fomento, Rouanet e contratos com freelancers exigem CNPJ; também simplifica receber da Steam.
Receber da Steam: formulário fiscal dos EUA (W-8BEN para pessoa física, W-8BEN-E para empresa) no Steamworks, para aplicar o tratado e evitar retenção maior.
Marca: registrar Echoes of the Shatter no INPI e, se o mercado americano for importante, no USPTO.
Software: registrar o programa de computador no INPI (protege o código e serve de prova de autoria). O Marco Legal também incluiu os jogos na Lei de Propriedade Industrial (art. 20); confirmar com advogado o que isso muda no registro.
Contratos com freelancers: cessão de direitos autorais por escrito para toda arte, música e código de terceiros. Sem isso, o estúdio não é dono dos assets.

### Checklist legal por fase
F1–F2 (protótipo)
Contratos de cessão de direitos com qualquer pessoa que contribuir com arte, áudio ou código
Registrar licença e origem de todo asset de terceiros (já previsto na seção 9)
Conversar com contador sobre MEI ou ME e a CNAE adequada
F3 (demo e página na Steam)
Abrir CNPJ antes de pagar o Steam Direct e preencher o formulário fiscal (W-8BEN-E)
Preencher o questionário de classificação indicativa do Steamworks antes de publicar a página; sem ele, a página não aparece no Brasil
Declarar no questionário de conteúdo da Steam qualquer uso de IA generativa
Publicar política de privacidade em português simples (telemetria opt-in, Sentry sem IP, nada de perfilamento)
Pedir o registro da marca no INPI
Acompanhar editais (Finep, estaduais e municipais) com a demo em mãos
F4–F5 (Acesso Antecipado)
Revisão com advogado de games: termos de uso, privacidade, classificação e enquadramento no ECA Digital
Registrar o programa de computador no INPI
Avaliar Rouanet ou Lei do Audiovisual para financiar o Ato II
Linhas vermelhas para o futuro (1.0 em diante)
Nunca vender baús, chaves, sorteios ou qualquer recompensa aleatória por dinheiro real (ECA Digital, art. 20).
Nunca dar prêmios com valor real nem reintroduzir cripto ou NFT (Marco Legal, art. 5º; política da Steam).
Coop ou chat só com: interação desligada por padrão, denúncia com resposta, bloqueio, recurso contra punição, controle parental e termos de uso (Marco Legal, art. 16; ECA Digital, art. 21).
Qualquer compra fora da Steam precisaria vir bloqueada para menores por padrão (Marco Legal, art. 17).

### Fontes
Lei 14.852/2024 (Marco Legal dos Games), Planalto
Lei 15.211/2025 (ECA Digital), Planalto
ECA Digital entra em vigor: o que muda para jogos (Souto Correa)
Decreto do Marco Legal: Rouanet Games e crédito do FSA (Adrenaline)
Portaria 1.048/2025 de classificação indicativa (TJDFT)
Classificação indicativa de jogo no Brasil e questionário da Steam (CursoGame)
Steam oculta no Brasil jogos sem classificação (fórum da Steam)