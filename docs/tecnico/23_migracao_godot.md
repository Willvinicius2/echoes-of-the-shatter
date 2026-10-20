# 23 — Migração da Unity para o Godot (20/10/2026)

Decisão do dono (Will), 20/10/2026: o jogo deixa a Unity e passa a ser feito no **Godot 4 (.NET, C#)**, com o Godot MCP controlando o editor. A análise anterior (`analises/unity-vs-godot-20261020.md` na pasta do projeto) recomendava ficar na Unity; o dono decidiu migrar mesmo assim, para um escopo menor e um ciclo de teste que os agentes consigam rodar. Esta decisão substitui a de 16/10/2026 (Unity 6.3).

## O que muda e o que fica

| Parte | Destino |
|---|---|
| ShatterCore (C++17), testes, CI do core | Fica sem mudança. Vira biblioteca nativa (`shattercore.dll` no Windows, `.so` no Linux) chamada por P/Invoke do C# do Godot |
| Bindings C# do core (`Interop`, 78 arquivos, C# puro) | Movidos para `ShatterCore/bindings/csharp/`; o projeto Godot os inclui como código-fonte |
| CSV, `Loc/`, `Story/`, esquemas, validadores | Ficam em `EchoesOfTheShatter/Content/Data/` por enquanto. Quando o projeto Godot existir, o destino é `godot/Data/` (mover num PR só, ajustando `tools/dados` e `core.yml`) |
| Modelos FBX, texturas e JSON do kit da Cripta | Copiados sem os `.meta` para `art-src/herdado-unity/` (entram no Godot por importação) |
| Cenas, prefabs, materiais URP, controllers, VFX, UI Toolkit, builders de editor, testes Unity | Removidos do `master`. Continuam no branch `arquivo/unity-final` (commit `61a5a20`) |
| Protótipo Godot F1 | Segue em `prototipos/godot-f1/` como referência de game feel (2D, GDScript) |
| Documentos de design, arte aprovada, prompts, pipeline TripoSG → Blender | Sem mudança |

O Git não deixou criar a tag `unity-final` (push de tag recusado no ambiente da nuvem); o branch `arquivo/unity-final` cumpre o mesmo papel. Quem tiver acesso pode criar a tag em cima dele.

## Pasta do projeto Godot

`godot/` na raiz do repositório (`godot/project.godot`). Quem cria o esqueleto é a thread "Cripta no Godot", no PC do Will; este PR não cria `godot/` para não colidir. Estrutura sugerida: `godot/scenes/`, `godot/scripts/` (com `Core/` apontando os bindings), `godot/ui/`, `godot/assets/`, `godot/tests/`.

## Regras que continuam valendo

- Nenhuma regra de jogo em C#/GDScript fora de chamadas ao core. Nenhum número de balanceamento no código. Nenhum texto visível no código, só chaves de localização.
- Determinismo do core inalterado.
- Toda arte nova passa pela aprovação do dono. O Mago usa capuz e cajado com cristal.
- O visual alvo continua o de `docs/arte/08_decisoes_visual_3d.md`, mas o escopo é menor (ver abaixo); as decisões de URP (pós-processamento, shaders) viram equivalentes no renderizador do Godot e serão registradas aqui quando testadas.

## Escopo e ordem

1. **Cripta** (mapa sombrio, objetos aprovados) montada no Godot, via MCP.
2. Guerreiro jogável: movimento, câmera 3/4, golpe, ligados ao core.
3. Inimigos da Cripta e o Guardião.
4. NPCs e Refúgio (depois da Cripta fechar).
5. Expedições idle, loot, inventário e UI completos.

A pendência `foco-fatia-vertical` (docs/20) segue valendo: Fase B e artes novas ficam congeladas até o Guerreiro fechar a Cripta.

## O que deixou de valer

- `docs/tecnico/04_arquitetura.md`: as seções de Unity (3 renderização URP, 4 asmdef, 9 integração, 13 testes, 17 pipeline Unity) são **histórico**. As seções do core, dados e contratos continuam. O cliente Godot terá a sua seção aqui, ao ser definido.
- Pendência `paginacao-windows` (memória virtual da Unity) e as regras de `unity.lock`/batchmode: sem objeto.
- `tools/cliente/checar_cliente.sh` e o workflow `cliente.yml`: removidos. O cliente Godot terá checagem própria (Godot headless + testes), a definir.

## Pendente de definição (a decidir com o código à mão)

- Versão exata do Godot 4.x e do .NET SDK; como carregar a biblioteca nativa no export (Windows primeiro).
- Framework de teste do cliente (GdUnit4 para C# ou testes headless próprios).
- Mover `Content/Data` para `godot/Data`.
