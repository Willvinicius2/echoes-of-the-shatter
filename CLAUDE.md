# Echoes of the Shatter — instruções para o Claude Code

ARPG single-player em 3D estilizado (câmera fixa 3/4) com expedições idle, para Steam (Acesso Antecipado).
Motor: **Unreal Engine 5.8, C++** (UE5 decidido em 15/10/2026 e versão 5.8 em 16/10/2026; o plano original dizia Godot 4).

## Direção de arte (aprovada em 16/10/2026)
- O visual segue o estilo do Spell Brigade: 3D estilizado pintado à mão, heróis chibi, magia em neon e UI de pedra escura. As decisões de renderização estão em `docs/08_decisoes_visual_3d.md`.
- As referências aprovadas e as folhas oficiais de heróis, inimigos, chefes, cenários e ícones estão em `docs/arte/referencias-geracao/` (ver o README dessa pasta). Todo personagem novo deve seguir essas folhas.
- Os assets extraídos do Spell Brigade (`D:\openclaude\spell-brigade-re`) servem só de referência de estilo. Nunca entram no projeto nem no build.
- O Mago usa capuz e cajado com cristal, e nunca lanterna.

## Onde está cada coisa
- `docs/00_plano_existente.md` — plano de design aprovado (Plano Steam v2.0). Fonte de verdade de regras, conteúdo e escopo; as partes de pixel art e Godot ficaram como histórico.
- `docs/01_plano_execucao.md` — equipe de 12 agentes, fases e quem é dono de cada arquivo.
- `docs/02_requisitos.md` — escopo do protótipo, RF-01..RF-65, RNF, critérios de aceite ([SC] = teste automático, [UE] = manual no editor).
- `docs/03_design_system.md` + `docs/03_design_tokens.json` — especificação de arte 3D (proporções, texel, pintura), paleta, tokens, telas e componentes UMG.
- `docs/04_arquitetura.md` — arquitetura UE 5.8, renderização 3D (câmera, materiais, sombras, Niagara), pipeline Blender → UE, orçamentos por asset e por cena, contratos, Build.cs, determinismo.
- `docs/08_decisoes_visual_3d.md` — decisões de renderização e quem é dono de cada número (03 = arte, 04 = orçamentos técnicos).
- `ShatterCore/` — motor de regras em C++17 puro, sem Unreal. Headers prontos em `include/shatter/`; `src/` ainda vazio.
- `EchoesOfTheShatter/Content/Data/schemas/` — esquemas das tabelas CSV (parcial).
- `tools/validate_data.py` — validador de dados (parcial, não testado contra CSV reais).

## Regras do projeto
- Texto em português do Brasil; código, IDs de conteúdo e chaves em inglês (`skill.warrior.iron_cut`).
- Um único motor de regras (ShatterCore) para combate e simulador idle. O módulo UE não calcula regra.
- Determinismo: mesma seed + dados + snapshot = mesmo resultado. Simular em 1 ou N partes dá o mesmo `resultHash`.
- Proibido em `ShatterCore/src/`: exceções, RTTI, estado global mutável, `std::rand`/`random_device`/distribuições da STL, iterar `unordered_map` em código que afeta resultado, `pow/exp/log/sin` no golpe e no simulador, `-ffast-math`.
- Números em CSV/JSON com `std::from_chars`/`std::to_chars` (ponto decimal).
- Nenhum número de balanceamento no código: tudo em `EchoesOfTheShatter/Content/Data/*.csv`.
- Nenhum texto visível ao jogador em C++/Blueprint: só chaves de localização.
- Evitar nomes que colidem com macros do UE: `check`, `verify`, `ensure`, `TEXT`, `PI`.
- **Agentes de design do jogo (conteúdo, narrativa, UI, revisões de design) usam no máximo o modelo Sonnet 5.5.**

## Como compilar e testar o ShatterCore
```
cmake -S ShatterCore -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build
ctest --test-dir build --output-on-failure
```

## Pendências de decisão
- Itens "confirmar no 5.8" do `docs/04_arquitetura.md`: conferir na instalação do motor antes de o Frontend depender deles.
- PC de entrada para medir a RNF-04 (pergunta P-4) ainda não definido; a seção 18 do `04` usa um placeholder.
- O `04` prevê Git LFS para arte e `.uasset`; o repositório ainda não tem LFS nem remoto, e as referências PNG já commitadas estão no Git comum.
- O protótipo Godot F1 continua na raiz (`project.godot`, `autoload/`, `core/`, `data/`, `game/`, `scenes/`, `tests/`) como referência de game feel. Ele não faz parte do jogo UE.

## Próximo passo
Retomar a Fase 2 (ver `docs/07_proximos_passos.md`): Data Engineer termina os CSV e o 06_dados.md, depois Narrative & Content e Backend Engineer; Frontend Engineer cria o projeto UE 5.8.
