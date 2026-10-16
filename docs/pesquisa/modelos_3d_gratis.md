# Modelos 3D grátis para Echoes of the Shatter (pesquisa, 2026-10-16)

Legenda: **[V]** = visto na página oficial/consultada; **[I]** = inferência minha (não confirmada em página); **[T]** = site/blog de terceiros, não verificado. Nada foi baixado, instalado ou executado.

## Parte A. Packs 3D gratuitos (provisórios)

| Pack | Página oficial | Licença [V] | Tamanho (grátis) [V] | Formatos [V] | Rig / animações |
|---|---|---|---|---|---|
| KayKit Adventurers 2.0 | https://kaylousberg.itch.io/kaykit-adventurers | CC0, uso comercial, sem atribuição | Free 12 MB (Extra 18, Source 23) | FBX, GLTF | Rigado, só animações básicas de movimento; 75 anims na versão Source. Free: Knight, Barbarian, Rogue (+Hooded), Mage, Ranger. Extra (pago, $7,95): Engineer, Druid, Barbarian_Large |
| KayKit Skeletons 1.1 | https://kaylousberg.itch.io/kaykit-skeletons | CC0 | Free 7,7 MB (Extra 12, Source 15) | FBX, GLTF | Rigado, anims básicas. Free: Warrior, Rogue, Mage, Minion (armas/escudos). Extra ($7,95): Golem (chefe), Necromancer |
| KayKit Dungeon Remastered 1.1 | https://kaylousberg.itch.io/kaykit-dungeon-remastered | CC0 | Free 31 MB (Extra 36, Source 39) | FBX, GLTF, OBJ (+FBX p/ Unity) | Estático. ~200 assets grátis (paredes, pisos, escadas, portas, baús, barris, armadilhas, banners). Pilar/arco/sarcófago/braseiro/osso não confirmados na descrição; podem existir [I] |
| KayKit Character Animations 1.1 | https://kaylousberg.itch.io/kaykit-character-animations | CC0 | Free 14 MB (Source 23 MB, $14,99) | FBX, GLTF | 161 anims humanoides (150+ grátis): General, Movement, Melee Combat, Ranged, Special etc. Rig_Medium (100+) e Rig_Large (25+) |
| Quaternius Universal Animation Library | https://quaternius.itch.io/universal-animation-library | CC0 | Standard 15 MB (Pro 41 MB, $9,99) | export p/ Unity | 45 anims grátis: locomoção 8 direções, morte, combate; idle/hit/esquiva não listados. Rig humanoide universal com retargeting; compatível com Mixamo |
| Quaternius Ultimate Monsters | https://quaternius.com/packs/ultimatemonsters.html | CC0 | não informado | FBX, OBJ, Blend, glTF | 50 monstros animados (texturização ambígua) |
| Quaternius RPG Character Pack | https://quaternius.com/packs/rpgcharacters.html | CC0 | não informado | FBX, OBJ, Blend, glTF | 6 personagens fantasia, rig, animados, texturizados |
| Quaternius Modular Dungeons | https://quaternius.com/packs/modulardungeon.html | CC0 | não informado | FBX, OBJ, Blend | 48 modelos sem animação e sem textura; pilares/arcos etc. não citados |
| Quaternius Bestiary Dungeon Monsters Kit | https://quaternius.com/packs/bestiarydungeonmonsterskit.html | "Free" pela QAL da Quaternius (texto da QAL não lido) | não informado | FBX, GLB | 7 monstros, rig Humanoid, compatível com a Universal Animation Library; anims do kit não listadas |
| Kenney (Modular Dungeon Kit, Mini Dungeon) | https://kenney.nl/assets/category:3D | Não confirmada (a página só mostrou "All rights reserved"/ToS). Kenney costuma ser CC0 [I]; conferir em cada pack | n/d | n/d | Estático |

### Compatibilidade com Humanoid da Unity
- KayKit: resposta do autor no itch.io (via busca [T]) diz que os personagens são rigs humanoides; basta mudar Rig > Animation Type de Generic para Humanoid, e usar "Copy from other Avatar" com o Rig_Medium_Avatar do pack gratuito. A página oficial do pack de animações não cita Humanoid: diz que funciona com personagens KayKit e retarget em outros humanoides [V].
- Barbarian_Large e Golem usam Rig_Large (menos animações) [I].
- Quaternius UAL: rig humanoide universal com retargeting; Humanoid da Unity não é citado explicitamente [V]. Teste de 10 minutos no Editor recomendado [I].

### Cobertura do elenco (inferência minha)
| Personagem do jogo | Melhor candidato grátis | Observação |
|---|---|---|
| Guerreiro (martelo de bloco e escudo) | KayKit Knight ou Barbarian (Adventurers Free) | Escudo/arma vêm como acessórios; martelo de bloco pode exigir modelo próprio |
| Arqueira | KayKit Ranger | Cobre |
| Mago (capuz pontudo, cajado com cristal) | KayKit Mage | Conferir se o cajado tem cristal (nunca lanterna) |
| Sentinela Oca (armadura vazia) | KayKit Skeletons Warrior/Minion | Aproximação |
| Cão de Cinza | Quaternius Ultimate Monsters (procurar quadrúpede) | Não verificado se há cão |
| Arqueiro Espectral | KayKit Skeletons Rogue/Minion com arco + material translúcido | Aproximação |
| Arauto de Pedra (constructo) | KayKit Golem (Extra, pago) ou monstro Quaternius | Custo zero => Quaternius |
| Guardião da Cripta (chefe) | KayKit Barbarian_Large/Golem (pagos); grátis: Warrior escalado | Aproximação |
| Cenário cripta | KayKit Dungeon Remastered Free + Quaternius Modular Dungeons | Faltas prováveis: sarcófago, braseiro |

Observações: nomes exatos das animações (idle, golpe sofrido, esquiva) não aparecem nas páginas; só categorias. O estilo é low-poly de gradiente, não o 3D pintado à mão do Spell Brigade; serve como provisório [I].

## Parte B. Imagem para 3D local (RTX 4060 Ti 8 GB, Windows)

| Modelo | VRAM forma / textura | Windows | Pesos / disco | Licença | Textura | Qualidade p/ estilizado [I] |
|---|---|---|---|---|---|---|
| Hunyuan3D-2 (2.0) via WinPortable (mmgp) | portable: forma >=3 GB, textura >=6 GB, RAM >=24 GB [V] | Sim (build cu126 p/ Ada) | repo HF 74,9 GB com todas as variantes [V]; uso real bem menor [I] | Tencent Hunyuan Community | Sim (paint v2.0) | Forma boa, textura média |
| Hunyuan3D-2mini | forma: não informado na página; 0,6B params [V] | Sim (mesmo portable) | repo HF 25,3 GB com variantes [V] | Tencent Hunyuan Community | Só forma na página; textura via paint 2.0 [I] | Forma boa, leve |
| Hunyuan3D-2GP (deepbeepmeep) | forma 6 GB; forma+textura 24,5 GB; perfil 4 para 6-9 GB [V] | Sim; exige VS2022 p/ compilar [V] | Python 3.10, torch 2.5.1 cu124 [V] | Fork do Hunyuan 2 (LICENSE não lido; presumo a mesma) [I] | Sim | Igual ao 2.0 |
| Hunyuan3D-2.1 | oficial: 10 GB forma / 21 GB textura / 29 GB total [V]; portable: forma >=3 GB com otimização máxima [V] | Sim | repo HF 14,9 GB [V] | Tencent Hunyuan Community (ver abaixo) | Sim, PBR | Melhor das Hunyuan; textura em 8 GB é o ponto fraco |
| TRELLIS (1) | >=16 GB [V] | Não oficial [V] | image-large 1,2B [V] | MIT (submódulos variam) | Sim | Boa; sem folga em 8 GB |
| TRELLIS.2 | >=24 GB oficial, só Linux testado [V]; ComfyUI-Trellis2 (visualbruno) com wheels Windows e workflow "low VRAM" [T]; site comercial afirma 8 GB a 512, ~120 s [T] | Via ComfyUI fork, não oficial | 4B params [V] | MIT (+ nvdiffrast/nvdiffrec próprias) [V] | Sim, PBR completo | Melhor qualidade geral, risco alto em 8 GB |
| TripoSG | >=8 GB [V] | Não documentado [V] | HF 7,95 GB [V] | MIT | Não (só forma) [V] | Geometria excelente, sem textura |
| Stable Fast 3D / SPAR3D | VRAM não declarada [V] | n/d | ~1B / ~2B params [V] | Stability Community: grátis com receita anual <= US$ 1 mi [V] | Sim (UV, rugosidade/metálico), <1 s | Baixa poly, qualidade menor |
| Outros 2026 | Hunyuan3D 3.0/3.1 só API, não aberto [T]; Step1X-3D e Hi3DGen não verificados | n/d | n/d | n/d | n/d | n/d |

### Termos comerciais Hunyuan3D 2.1 (LICENSE lido) [V]
- Território: mundo todo exceto UE, Reino Unido e Coreia do Sul. O Brasil está dentro. Se o jogo for vendido na Steam em países da UE, não está claro se isso conta como uso fora do território (a licença fala em uso do modelo, não das saídas). Não resolvi; vale consultar advogado [I].
- Mais de 1 milhão de MAU exige licença da Tencent; irrelevante neste porte [I].
- O usuário é dono das saídas (6d). Proibido usar modelo ou saídas para treinar/melhorar outro modelo de IA (5b). Aviso "Notice" ao distribuir o modelo, não os assets.
- A política de uso aceitável pede identificar conteúdo gerado por máquina ao publicá-lo; pode implicar divulgar IA na página da Steam [I].
- MIT (TRELLIS, TripoSG): sem restrição territorial. Stability: ok abaixo de US$ 1 mi/ano.

## Recomendação
- **Principal: Hunyuan3D-2.1 via Hunyuan3D-2-WinPortable (YanWenKun)**: forma cabe em 8 GB, textura PBR com mmgp otimizado, caminho Windows mais testado. Riscos: restrição UE/UK/Coreia, 24 GB de RAM recomendados, textura lenta.
- **Reserva: TripoSG (MIT) para forma e textura feita no Blender/Unity**, ou TRELLIS.2 via ComfyUI-Trellis2 (MIT) se o teste a 512 em 8 GB funcionar.
- Sem custo e já: KayKit/Quaternius como provisórios.

## Lista do que baixar
1. KayKit Adventurers Free 2.0, 12 MB: https://kaylousberg.itch.io/kaykit-adventurers
2. KayKit Skeletons Free 1.1, 7,7 MB: https://kaylousberg.itch.io/kaykit-skeletons
3. KayKit Dungeon Remastered Free 1.1, 31 MB: https://kaylousberg.itch.io/kaykit-dungeon-remastered
4. KayKit Character Animations Free 1.1, 14 MB: https://kaylousberg.itch.io/kaykit-character-animations
5. Quaternius Ultimate Monsters (tamanho n/d): https://quaternius.com/packs/ultimatemonsters.html
6. Hunyuan3D-2-WinPortable, build cu126 (.7z.001/.002, tamanho n/d; modelos baixam sob demanda, 2.1 ~14,9 GB): https://github.com/YanWenKun/Hunyuan3D-2-WinPortable

## Fontes
- kaylousberg.itch.io (4 páginas acima); quaternius.com/packs/{ultimatemonsters,rpgcharacters,modulardungeon,bestiarydungeonmonsterskit}.html; quaternius.itch.io/universal-animation-library; kenney.nl/assets/category:3D
- github.com/Tencent-Hunyuan/Hunyuan3D-2.1 (e blob/main/LICENSE); github.com/deepbeepmeep/Hunyuan3D-2GP; github.com/YanWenKun/Hunyuan3D-2-WinPortable
- huggingface.co/tencent/Hunyuan3D-2, Hunyuan3D-2.1, Hunyuan3D-2mini; huggingface.co/VAST-AI/TripoSG; huggingface.co/stabilityai/stable-fast-3d e stable-point-aware-3d
- github.com/microsoft/TRELLIS, github.com/microsoft/TRELLIS.2, github.com/VAST-AI-Research/TripoSG
- Terceiros [T]: trellis2.app/blog/trellis-2-low-vram (site comercial), codersera.com (guia Hunyuan3D Windows), posts do autor KayKit no itch.io

## Lacunas
Tamanhos de download da Quaternius, VRAM real da 2mini, tamanho exato do WinPortable, licença Kenney, existência de sarcófago/braseiro/cão nos packs, Step1X-3D e novidades de 2026 não foram verificados. Testar na máquina antes de decidir.
