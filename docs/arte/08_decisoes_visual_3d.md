# Decisões de motor, renderização e arte (orquestrador, 16/10/2026)

Contexto: o dono aprovou o visual no estilo do Spell Brigade (24 referências em `docs/arte/referencias-geracao/aprovadas/`, README na mesma pasta). A pergunta P-1 de `docs/requisitos-qa/02_requisitos.md` está respondida: **3D estilizado**, não pixel art 2D.

**Motor (decisão do dono em 16/10/2026): Unity 6 LTS com URP, C#.** Substitui o Unreal Engine 5.8, que tinha substituído o Godot 4. Motivos:
- **Ativos em texto:** cenas, prefabs e ScriptableObjects são texto, e a CLI roda compilação e testes. O desenvolvimento com agentes fica mais autônomo e revisável.
- **Peso:** editor e build mais leves (meta de instalador abaixo de 500 MB e Steam Deck).
- **Estilo:** a referência visual foi feita em Unity/URP.
- **Custo:** gratuito no plano Personal até o limite de receita da Unity.

O ShatterCore continua em C++17 puro e vira uma DLL nativa chamada pelo C# via P/Invoke.

Decisões fechadas (não reabrir; detalhar e justificar):

1. **Forma:** malhas 3D low/mid poly com texturas pintadas à mão e luz/sombra assadas na textura (albedo pintado), rim por fresnel e emissivo para magia. Heróis chibi (cerca de 3 cabeças). Sem sprites, tiles 64×32, resolução interna 960×540, filtro nearest nem escala inteira.
2. **Personagens:** Skinned Mesh com Animator. Mínimo por classe, do plano: parado, andar, esquiva, ataque básico, 2 animações de habilidade reaproveitáveis (golpe e conjuração), tomar dano e morte. Inimigos com conjunto menor. Cenário: malhas estáticas modulares em prefabs (kits por área, como as folhas 07, 13 a 20).
3. **Câmera:** fixa em 3/4 com perspectiva de FOV estreito (pseudo-isométrica), yaw 45° fixo, pitch entre -50° e -60°, sem rotação pelo jogador, segue o herói com suavização. O Tech Lead fixa os números e o zoom. Números atuais na entrada de 16/10/2026 (câmera de 56 m) abaixo.
4. **Pipeline gráfico:** URP com Forward (ou Forward+) e MSAA (bordas limpas para o estilo pintado), sem iluminação global em tempo real. Sombras baratas (cascatas curtas ou sombra blob; o Tech Lead decide e justifica). Névoa com a cor-assinatura de cada área. Poucos shaders mestres em Shader Graph, parametrizados (personagem, cenário, VFX, UI). Meta de desempenho continua a RNF-04 (PC de entrada e Steam Deck).
5. **VFX:** sistema de partículas da Unity com Shader Graph; o VFX Graph só onde o ganho justificar (o Tech Lead decide). Efeitos do jogador finos e translúcidos com núcleo claro; ameaças inimigas opacas e quentes (telegraphs no chão), como nas folhas 09 e 22.
6. **UI:** UI Toolkit (UXML e USS) em resolução nativa com escala por DPI. Os tokens de `docs/arte/03_design_tokens.json` viram variáveis USS. Estilo da UI de pedra escura com molduras orgânicas e preenchimento "lava", como as folhas 10, 11 e 12.
7. **Fonte de verdade visual:** `docs/arte/referencias-geracao/` (folhas oficiais 02 a 08, 11, 21 a 24). Assets extraídos do Spell Brigade nunca entram no projeto nem no build. As imagens geradas são conceito: o plano exige assets finais feitos ou refeitos por artistas e declaração de uso de IA na Steam.
8. **Regras do jogo não mudam:** o ShatterCore, o determinismo, os dados em CSV e as regras de combate ficam como estão. A mudança é só de apresentação.

## Donos e números reconciliados

- **Dono de cada número:** o `docs/arte/03_design_system.md` é dono da especificação de arte (proporções, alturas, densidade de texel, regras de pintura, cores). O `docs/tecnico/04_arquitetura.md` é dono dos orçamentos técnicos (triângulos e texturas por asset, LOD, orçamento por cena, FPS). Um documento cita o outro e não repete o número.
- **Altura do herói:** 150 cm (chibi, cerca de 3 cabeças). A cápsula e o enquadramento da câmera seguem essa altura.
- **Triângulos no LOD0:**
  - Teto duro e alvo de produção (régua do Spell Brigade, `docs/arte/regua_spell_brigade.md`; o 04, seção 17.2, é o dono).
  - Herói: teto 10.000; alvo 4.000 a 6.500.
  - Inimigo comum: teto 5.000; alvo 1.500 a 3.500. Enxame: alvo 500 a 1.500.
  - Elite: usa a mesma malha do inimigo comum, mudando só tinta, halo e escala até ×1,15. Não tem malha própria.
  - Chefe: teto 25.000; alvo 10.000 a 16.000.
  - Props e módulos de cenário: segundo a tabela do `04`.
- **Ossos:** herói 55, inimigo 35 e chefe 100, no máximo.
- **Texturas:**
  - Herói: 1024² (máscara 512²). Inimigo: 512² (máscara 256²). Mantidos em 16/10/2026: a proposta de 2048² e 1024² do 03 foi recusada pelo 04 (herói com ~88 px a 56 m, memória do Deck, mipmaps; ver 04, seção 17.2).
  - Chefe: 2048² num slot só, ou 2 slots de 1024².
  - Kit de área: até 4 folhas de 2048².
  - Sem normal map: o volume vem da pintura.
- **LOD:** trocas em 14 m e 24 m do herói (eram 18 e 32 m antes da câmera de 56 m), ponto de partida a medir na F1.
- **Orçamento por cena:** só os números do `04`, seção 18.
- **FPS:** a meta é 60 FPS (RNF-04). O Steam Deck aceita um piso de 40 FPS no modo 40 Hz, se a medição na F1 exigir.

## Entrada de 16/10/2026: câmera a 56 m e escala de mapa

- **Decisão do dono:** distância padrão da câmera de **56 m** (antes 42 m), faixa de 48 a 66 m. Pitch 55°, yaw 45°, FOV vertical 14,2° e plano distante de 150 m não mudam.
- **Motivo:** ao testar a cena base no Unity, o dono achou os 42 m com "cara de jogo de celular". Ele quer visão de ARPG de PC ou MMO e mapas maiores. A 56 m a tela mostra ~24,8 × 14,0 m (antes ~18,6 × 10,5 m) e o herói tem ~88 px de altura em 1080p (o graybox mediu 117 px a 42 m).
- **Consequências no 04:** sombra com distância de 90 m (3.6); tremor de câmera máx. 0,11 m (escalado por 56/42); raio do fade de oclusão ~4 m; LODs a 14 e 24 m; alvos de produção de triângulos abaixo dos tetos (17.2); nota de orçamento por cena (18). Os tetos duros não mudaram.
- **Escala de mapa (decidida pelo dono no mesmo dia):** zona A. Arena de 40 × 40 m (a do Guardião tem pilares), salas de 24 a 32 m, corredores de 6 m. A zona B (arena 56 m) fica na cena base só como comparação.
- **Ferramenta de desenvolvimento:** `Assets/Scenes/Sandbox/Base_Escala.unity` com `CameraDistanceTuner`, `DevZoneTeleport` e `SandboxBuilder` (detalhes no 04, seção 3.2).
- **A medir na F1:** legibilidade do herói de 88 px, definição da sombra a 90 m e batches de cenário.
- **Zoom mínimo de legibilidade:** herói com pelo menos 75 px (1080p) e 55 px (Deck) no zoom mais afastado; o zoom trava aí (04, seção 3.2). Os 66 m cumprem os dois pisos.
