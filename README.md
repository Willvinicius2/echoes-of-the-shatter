# Echoes of the Shatter

ARPG single-player em 3D estilizado, com câmera fixa 3/4 e expedições idle, para PC (Steam, Acesso Antecipado).
Três heróis no lançamento: Guerreiro, Arqueiro e Mago. O visual segue o estilo pintado à mão do Spell Brigade.

- **Motor:** Unity 6.3 LTS (`6000.3.26f1`) com URP, em C#.
- **Regras do jogo:** ShatterCore, em C++17, compilado como DLL e chamado pela Unity. Combate e simulador idle usam o mesmo motor.
- **Estado atual:** etapa 2 de 5, a fatia jogável da Cripta. O andamento de cada setor está no painel.

## Acompanhar sem abrir o código

| O quê | Onde |
|---|---|
| Painel de produção: etapas, setores, perguntas para votar, decisões e galeria | https://claude.ai/artifact/7Kzo46Eyy8cQjF9HhuWMXg |
| Roteiro: todos os documentos e as artes aprovadas | https://claude.ai/artifact/5G5WBocgrp8NAeLKiF9FP8 |
| As 5 etapas do jogo e os critérios de cada uma | [`docs/15_etapas.md`](docs/15_etapas.md) |
| Plano completo do jogo | [`docs/00_plano_existente.md`](docs/00_plano_existente.md) |

Os links do painel e do roteiro só abrem para quem foi convidado pelo dono.

## Baixar e abrir

1. Instale o [Git](https://git-scm.com/) e o [Git LFS](https://git-lfs.com/). Sem o LFS, modelos, texturas e a DLL chegam como arquivos vazios.
2. Clone e baixe os arquivos grandes:
   ```
   git clone https://github.com/Willvinicius2/echoes-of-the-shatter.git
   cd echoes-of-the-shatter
   git lfs pull
   ```
3. Instale pelo Unity Hub exatamente a versão **6000.3.26f1**. Outra versão reimporta o projeto inteiro e gera mudanças em centenas de arquivos.
4. No Unity Hub, use **Add** e escolha a pasta `EchoesOfTheShatter/`, que fica dentro do repositório.

## Pastas

| Pasta | Conteúdo |
|---|---|
| `EchoesOfTheShatter/` | Projeto Unity: `Assets/` (cenas, scripts, arte), `Content/Data/` (tabelas CSV, textos pt_BR e en, esquemas) |
| `ShatterCore/` | Motor de regras em C++17, com testes |
| `docs/` | Plano, requisitos, design system, arquitetura, dados, QA, etapas, pesquisa |
| `docs/arte/referencias-geracao/aprovadas/` | Artes aprovadas: heróis, inimigos, chefes, cenários, ícones e folhas de modelagem |
| `docs/progresso/` | `estado.json` (fonte do painel) e o painel gerado |
| `art-src/` | Arquivos de arte de origem: Blender, graybox e o pipeline de acabamento dos modelos |
| `tools/` | Validador de dados, build do ShatterCore e geradores do painel e do roteiro |
| `.claude/` | Agentes e configuração do Claude Code usados na produção |

A raiz também guarda o protótipo antigo em Godot (`project.godot`, `core/`, `game/` etc.). Ele serve só de referência de game feel; veja [`docs/prototipo_godot_f1.md`](docs/prototipo_godot_f1.md).

## Testar

- **ShatterCore no Windows:** `tools\build_core.cmd Release --werror` (precisa do Visual Studio Build Tools). Em Linux, ver o `CLAUDE.md`.
- **Tabelas de dados:** `python tools/validate_data.py`
- **Unity:** Window > General > Test Runner, testes EditMode.
- O CI do GitHub compila e testa o núcleo e valida as tabelas a cada push e pull request para o `master`.

## Como trabalhamos

- Cada frente de trabalho tem sua branch (`etapaN/<frente>`). O merge no `master` vem depois dos testes.
- Todo commit vai para o GitHub logo depois de feito, para o repositório sempre mostrar o estado real.
- Mensagens de commit seguem o padrão Conventional Commits, em português (`feat(...)`, `fix(...)`, `docs(...)`).
- Arte nova só entra no jogo depois da aprovação do dono.
- Evite que duas pessoas mexam na mesma cena ou no mesmo prefab da Unity ao mesmo tempo: conflito nesses arquivos é difícil de resolver.
- As regras completas do projeto, para pessoas e para o Claude Code, estão no [`CLAUDE.md`](CLAUDE.md).
