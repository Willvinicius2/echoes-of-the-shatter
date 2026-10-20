# Echoes of the Shatter

ARPG single-player em 3D estilizado, com câmera fixa 3/4 e expedições idle, para PC (Steam, Acesso Antecipado).
Três heróis no lançamento: Guerreiro, Arqueiro e Mago. O visual segue o estilo pintado à mão do Spell Brigade.

- **Motor:** Godot 4 (.NET, C#). Migrado da Unity em 20/10/2026; ver [`docs/tecnico/23_migracao_godot.md`](docs/tecnico/23_migracao_godot.md). O último estado da Unity está no branch `arquivo/unity-final`.
- **Regras do jogo:** ShatterCore, em C++17, compilado como biblioteca nativa e chamado pelo Godot por P/Invoke. Combate e simulador idle usam o mesmo motor.
- **Estado atual:** etapa 2 de 5, a fatia jogável da Cripta. O andamento de cada setor está no painel.

## Acompanhar sem abrir o código

| O quê | Onde |
|---|---|
| Painel de produção: etapas, setores, perguntas para votar, decisões e galeria | https://claude.ai/artifact/7Kzo46Eyy8cQjF9HhuWMXg |
| Roteiro: todos os documentos e as artes aprovadas | https://claude.ai/artifact/5G5WBocgrp8NAeLKiF9FP8 |
| As 5 etapas do jogo e os critérios de cada uma | [`docs/design/15_etapas.md`](docs/design/15_etapas.md) |
| Plano completo do jogo | [`docs/design/00_plano_existente.md`](docs/design/00_plano_existente.md) |

Os links do painel e do roteiro só abrem para quem foi convidado pelo dono.

## Baixar e abrir

1. Instale o [Git](https://git-scm.com/) e o [Git LFS](https://git-lfs.com/). Sem o LFS, modelos, texturas e a DLL chegam como arquivos vazios.
2. Clone e baixe os arquivos grandes:
   ```
   git clone https://github.com/Willvinicius2/echoes-of-the-shatter.git
   cd echoes-of-the-shatter
   git lfs pull
   ```
3. Instale o Godot 4 (edição .NET) e o .NET SDK. O projeto Godot fica em `godot/` (criado na migração; veja `docs/tecnico/23_migracao_godot.md`).

## Pastas

| Pasta | Conteúdo |
|---|---|
| `godot/` | Projeto Godot (cenas, scripts, UI); criado na migração |
| `EchoesOfTheShatter/Content/Data/` | Tabelas CSV, textos pt_BR e en e esquemas (vão para `godot/Data/` depois) |
| `ShatterCore/` | Motor de regras em C++17, com testes; `bindings/csharp/` tem o P/Invoke em C# para o Godot |
| `docs/` | Documentos por assunto (`design/`, `tecnico/`, `requisitos-qa/`, `arte/`, `pesquisa/`); índice em `docs/README.md` |
| `docs/arte/referencias-geracao/aprovadas/` | Artes aprovadas: heróis, inimigos, chefes, cenários, ícones e folhas de modelagem |
| `docs/progresso/` | `estado.json` (fonte do painel) e o painel gerado |
| `art-src/` | Arquivos de arte de origem: Blender, graybox, pipeline de acabamento e `herdado-unity/` (modelos e texturas vindos da Unity) |
| `tools/` | Validador de dados, build do ShatterCore e geradores do painel e do roteiro |
| `.claude/` | Agentes e configuração do Claude Code usados na produção |

O protótipo antigo em Godot fica em `prototipos/godot-f1/`. Ele serve só de referência de game feel; veja [`prototipos/godot-f1/COMO_RODAR.md`](prototipos/godot-f1/COMO_RODAR.md).

## Testar

- **ShatterCore no Windows:** `tools\core\build_core.cmd Release --werror` (precisa do Visual Studio Build Tools). Em Linux, ver o `CLAUDE.md`.
- **Tabelas de dados:** `python tools/dados/validate_data.py`
- **Cliente Godot:** testes ainda a definir (ver doc 23).
- O CI do GitHub compila e testa o núcleo e valida as tabelas a cada push e pull request para o `master`.

## Como trabalhamos

- Cada frente de trabalho tem sua branch (`etapaN/<frente>`). O merge no `master` vem depois dos testes.
- Todo commit vai para o GitHub logo depois de feito, para o repositório sempre mostrar o estado real.
- Mensagens de commit seguem o padrão Conventional Commits, em português (`feat(...)`, `fix(...)`, `docs(...)`).
- Arte nova só entra no jogo depois da aprovação do dono.
- Evite que duas pessoas editem a mesma cena `.tscn` ao mesmo tempo.
- As regras completas do projeto, para pessoas e para o Claude Code, estão no [`CLAUDE.md`](CLAUDE.md).
