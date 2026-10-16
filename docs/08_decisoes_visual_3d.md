# Decisões de renderização e arte (orquestrador, 16/10/2026)

Contexto: o dono aprovou o visual no estilo do Spell Brigade (24 referências em `docs/arte/referencias-geracao/aprovadas/`, README na mesma pasta). Motor: Unreal Engine 5.8, C++. A pergunta P-1 de `docs/02_requisitos.md` está respondida: **3D estilizado**, não pixel art 2D.

Decisões fechadas (não reabrir; detalhar e justificar):

1. **Forma:** malhas 3D low/mid poly com texturas pintadas à mão e luz/sombra assadas na textura (albedo pintado), rim por fresnel e emissivo para magia. Heróis chibi (cerca de 3 cabeças). Sai Paper2D, flipbooks, sprites, tiles 64×32, resolução interna 960×540, filtro nearest e escala inteira.
2. **Personagens:** Skeletal Mesh com animações. Mínimo por classe, do plano: parado, andar, esquiva, ataque básico, 2 animações de habilidade reaproveitáveis (golpe e conjuração), tomar dano e morte. Inimigos com conjunto menor. Cenário: Static Mesh modular (kits por área, como as folhas 07, 13 a 20).
3. **Câmera:** fixa em 3/4 com perspectiva de FOV estreito (pseudo-isométrica), yaw 45° fixo, pitch entre -50° e -60°, sem rotação pelo jogador, segue o herói com suavização. O Tech Lead fixa os números e o zoom.
4. **Pipeline gráfico:** Forward Shading com MSAA (bordas limpas para o estilo pintado), sem Lumen, sem Nanite, sem Virtual Shadow Maps. Sombras baratas (CSM curto ou sombra de contato/blob, o Tech Lead decide e justifica). Exponential Height Fog com a cor-assinatura de cada área. Materiais mestres poucos e parametrizados (personagem, cenário, VFX, UI). Meta de desempenho continua a RNF-04 (PC de entrada e Steam Deck).
5. **VFX:** Niagara. Efeitos do jogador finos e translúcidos com núcleo claro; ameaças inimigas opacas e quentes (telegraphs no chão), como nas folhas 09 e 22.
6. **UI:** UMG em resolução nativa com a curva de DPI padrão do UE (não mais escala inteira nem fonte pixel). Estilo da UI de pedra escura com molduras orgânicas e preenchimento "lava", como as folhas 10, 11 e 12.
7. **Fonte de verdade visual:** `docs/arte/referencias-geracao/` (folhas oficiais 02 a 08, 11, 21 a 24). Assets extraídos do Spell Brigade nunca entram no projeto nem no build. As imagens geradas são conceito: o plano exige assets finais feitos ou refeitos por artistas e declaração de uso de IA na Steam.
8. **Regras do jogo não mudam:** o ShatterCore, o determinismo, os dados em CSV e as regras de combate ficam como estão. A mudança é só de apresentação.

## Donos e números reconciliados

- **Dono de cada número:** o `docs/03_design_system.md` é dono da especificação de arte (proporções, alturas, densidade de texel, regras de pintura, cores). O `docs/04_arquitetura.md` é dono dos orçamentos técnicos (triângulos e texturas por asset, LOD, orçamento por cena, FPS). Um documento cita o outro e não repete o número.
- **Altura do herói:** 150 cm (chibi, cerca de 3 cabeças). A cápsula e o enquadramento da câmera seguem essa altura.
- **Triângulos no LOD0:**
  - Herói: 7.000 a 10.000.
  - Inimigo comum: 3.500 a 5.000.
  - Elite: usa a mesma malha do inimigo comum, mudando só tinta, halo e escala até ×1,15. Não tem malha própria.
  - Chefe: 15.000 a 25.000.
  - Props e módulos de cenário: segundo a tabela do `04`.
- **Ossos:** herói 55, inimigo 35 e chefe 100, no máximo.
- **Texturas:**
  - Herói: 1024².
  - Inimigo: 512².
  - Chefe: 2048² num slot só, ou 2 slots de 1024².
  - Kit de área: até 4 folhas de 2048².
  - Sem normal map: o volume vem da pintura.
- **LOD:** trocas em 18 m e 32 m, ponto de partida a medir na F1.
- **Orçamento por cena:** só os números do `04`, seção 18.
- **FPS:** a meta é 60 FPS (RNF-04). O Steam Deck aceita um piso de 40 FPS no modo 40 Hz, se a medição na F1 exigir.
