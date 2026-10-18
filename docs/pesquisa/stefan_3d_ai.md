# Pesquisa de campo: canal Stefan 3D AI (@stefan_3d_ai)

Data da pesquisa: 16/10/2026. Pesquisador: agente pesquisador-referencias. Nada foi instalado, baixado ou executado.

## 1. Resumo

- O canal é de Stefan Vaskevich ("Stefan 3D AI"). Pelos posts dele no X e por terceiros, ele faz jogos 3D com Claude Code (Opus 5.5), Unity, Blender e Higgsfield, empacota o próprio fluxo em skills e abriu o workspace dele em repositório público.
- **Não foi possível listar os vídeos do canal.** A página `/videos` do YouTube devolve só o rodapé (título "Stefan 3D AI - YouTube"); o id do canal e o feed RSS não puderam ser obtidos. Só 3 vídeos foram identificados, por fontes indiretas. Nenhuma descrição de vídeo foi lida, então a lista de links das descrições é desconhecida.
- Ponto de atenção do projeto: o `CLAUDE.md` diz **Unreal Engine 5.8, C++** (decisão de 15 e 16/10/2026), mas `docs/tecnico/04_arquitetura.md` (seções 2, 9 e 17) ainda descreve **Unity 6 + URP + P/Invoke + FBX**. O pedido citou Unity. As recomendações abaixo valem para os dois motores quando possível e marcam onde dependem da decisão. Isso precisa ser resolvido pelo orquestrador e pelo dono.

## 2. Vídeos e itens analisados

Observado = lido na fonte citada. Nenhum vídeo foi assistido.

| Item | Data | Link | O que mostra | Nível de verificação |
|---|---|---|---|---|
| Vídeo "WoW-style game em 36h" | não confirmada (post no X de 2026) | post: https://x.com/Stefan_3D_AI/status/2104558611968229776 (link do vídeo estava encurtado e não abriu) | Segundo o post: Opus 5.5 no Claude Code construiu um jogo estilo WoW em 36 h; ele escreveu uma spec detalhada, deu acesso a Unity, Blender e Higgsfield e empacotou o fluxo próprio em skills | Só o texto do post, via snippet de busca. O X devolveu HTTP 402 no fetch direto |
| Vídeo do workspace open-source | 21/09/2026 (post) | post: https://x.com/Stefan_3D_AI/status/2102110035853922310 | Um repo com contexto do projeto, conhecimento e fluxos, para Claude Code, Codex, Blender e Unity usarem a mesma memória; todo asset do jogo passa por ele | Snippet da busca; vídeo não visto |
| Vídeo "plataforma 3D em 72 h" | não confirmada | resumo de terceiro: https://www.wesleychong.com/articles/ai-3d-game-72-hours-assethub-claude-code-unreal-mcp?lang=en | Fluxo: conceito, assets no AssetHub, rig, nível montado no Blender, importação no Unreal 5.8, gameplay com Claude Code + Unreal Engine MCP, playtest. Lições: escopo pequeno, uma ferramenta por tarefa, playtest decide | Resumo de terceiro (o artigo diz ser sobre o vídeo, mas não linka o vídeo). Atribuição não confirmada pelo canal |
| Post do repo | 12/10/2026 | https://x.com/Stefan_3D_AI/status/2109643581787095115 | Link do workspace no GitHub; cita MCPs gratuitos de Blender, Unity e Godot | Snippet |

Total: 3 vídeos identificados (1 só por post, 1 só por resumo de terceiro), mais o repositório. Não analisei nenhum vídeo por transcrição.

## 3. Ferramentas, skills, MCPs e conectores

| Item | Link | Custo | Licença | Observado / notas |
|---|---|---|---|---|
| Repositório Mr. Mak Workspace (witnesstodark) | https://github.com/witnesstodark/mr-mak-workspace | App grátis; exige contas próprias de agentes (Claude Code, Codex) | MIT (código e docs); skills de terceiros mantêm licença própria | Lido o README. App desktop (Tauri) com terminais de CLI de agentes, árvore de arquivos, relatórios; instalador Windows x64. 20 skills em `.agents/skills` espelhadas em `.claude/skills`: planejamento, handoff, geração de imagem (fal.ai, Higgsfield), ficha de personagem, Blender para animação de jogo, VFX, UI, integração de animação, level design, áudio, revisão visual. Pastas `context/`, `knowledge/`, `processes/`. Há manifesto SHA-256 opcional para entrega de assets. Os MCPs vêm vazios; o README não nomeia MCP de Unity ou Godot (diverge do post). O assistente de voz opcional usa OpenAI (pago) |
| Blender MCP (ahujasid) | https://github.com/ahujasid/blender-mcp | Grátis. Poly Haven grátis (CC0). Poly Pizza chave grátis. Rodin, Tripo, Hunyuan3D e Sketchfab precisam de chave/conta (preço não informado) | MIT | Lido o README. Roda no Windows. `execute_blender_code` roda Python arbitrário; socket sem autenticação (manter em localhost); existe modo seguro `BLENDER_MCP_SAFE_MODE=1`. Não confirmado que Stefan use exatamente este |
| Higgsfield | MCP "higgsfield" aparece na sessão do dono, ainda sem autorização (OAuth) | Pago (preço não verificado) | Serviço proprietário | Citado no post do WoW. Gera imagem/vídeo; não verificado se gera 3D |
| Skills de terceiros "blender-3d-asset-generation" e "unity-mcp-game-development" | https://github.com/lovecatisgood-sudo/3d-asset-generation-blender-unity-game-development-skills | Grátis | MIT | Sem ligação com Stefan (o README não o cita). Skills genéricas de bpy, UV, PBR, rig, LOD, export, QA com script de auditoria JSON. Origem pequena e com texto promocional de curso: tratar como referência de leitura, não instalar sem revisar |
| Unity MCP (IvanMurzak) | https://github.com/IvanMurzak/Unity-MCP | Grátis (open-source, não revisei a licença) | não verificada | Surgiu na busca como ponte Claude Code para o Editor Unity. Não confirmado como o usado por Stefan |
| AssetHub + Unreal Engine MCP | via https://www.wesleychong.com/articles/ai-3d-game-72-hours-assethub-claude-code-unreal-mcp?lang=en | Não informado | não verificada | Só no resumo de terceiro. Relevante se o motor for Unreal |
| Claude Code, Opus 5.5 | produto Anthropic | Assinatura/API que o dono já usa | proprietário | Base do fluxo |

Não verificado: se há outras skills/MCPs citados nas descrições dos vídeos (não li nenhuma descrição).

## 4. Encaixe no projeto

O projeto já tem: agentes por setor (`.claude/agents`), geração de conceito via Codex CLI + gpt-image com folhas oficiais de personagem (`docs/arte/referencias-geracao/`), ShatterCore em C++ e pipeline Blender para o motor (doc 04, seção 17). O gargalo declarado no README de referências: **não há ainda modelos 3D, rigs nem animações**; as folhas são só conceito.

Padrões úteis do canal, em ordem de impacto:

1. **Memória compartilhada em arquivos (contexto, conhecimento, processos) + skills do próprio fluxo.** Já fazemos parte disso (CLAUDE.md, docs, agentes). Ganho: transformar o que deu certo (ex.: scripts de `scripts/` de geração, regras de consistência dos prompts) em skills e em `knowledge/` reutilizáveis. Custo: zero (só texto). Risco: baixo; manter curto para não inflar contexto.
2. **Spec detalhada antes de deixar o agente construir.** Já temos GDD e docs numerados; o ganho é manter a spec como entrada única dos agentes. Custo zero.
3. **Blender MCP para o pipeline personagem/cenário (modelagem base, escala, cleanup, export).** Acelera preparar os modelos a partir das folhas. Custo grátis (MIT); geração 3D por IA (Rodin, Tripo, Hunyuan) é paga ou limitada e o preço não foi verificado. Riscos: Python arbitrário sem autenticação (usar modo seguro, localhost, salvar antes); qualidade de topologia/UV de IA geralmente pede retrabalho; o resumo do vídeo de 72 h diz que o agente não julga bem orientação espacial 3D.
4. **MCP do motor (Unity MCP ou Unreal MCP) para gameplay, prefabs/cenas e testes.** Ganho: o agente cria objetos e roda testes no editor. Depende da decisão Unity x Unreal. Risco: dá controle do editor ao agente; revisar permissões e sempre trabalhar em branch/Git. Custo: grátis nas opções vistas, versão e compatibilidade com Unity 6 / UE 5.8 por confirmar.
5. **Skills de animação no Blender e integração de animação (as do Mr. Mak Workspace).** Animação é a lacuna mais cara do projeto (README de referências, pontos em aberto). Vale ler as skills como modelo e adaptar às nossas folhas, em vez de instalar o app. Custo grátis (MIT); qualidade real não verificada (não vi resultados).
6. **Higgsfield para vídeo/imagem de referência de movimento.** Só se o dono quiser; é pago, preço não verificado, e já temos gpt-image via Codex. Prioridade baixa.
7. **Workspace desktop (Mr. Mak Workspace).** Útil para quem quer interface visual; para nós, que já usamos Claude Code e docs, o ganho é pequeno e adiciona um app Tauri e dependências. Prioridade baixa; só ler a estrutura como inspiração.

## 5. Riscos gerais

- Fontes indiretas: posts e resumos de terceiros; afirmações como "36 h" e "WoW-style" são autodeclaradas e não vi o resultado.
- Código e skills de terceiros rodam scripts (Blender Python, MCP com acesso ao editor): revisar antes de qualquer uso; não instalar a partir deste relatório sem decisão do dono.
- Assets gerados por IA: licença e originalidade não garantidas; manter a regra do projeto de não usar assets de terceiros no build.
- Divergência de motor (Unity x Unreal) pode invalidar parte dos itens 4 e dos pipelines da seção 17.

## 6. O que não foi possível verificar

- Lista de vídeos, datas, descrições e links do canal (YouTube não retornou conteúdo; X devolveu 402; LinkedIn 999).
- Conteúdo, transcrições e resultados dos vídeos.
- Os MCPs de Unity e Godot que o post de 12/10 menciona (o README do repo não os nomeia).
- Preços de Higgsfield, Rodin, Tripo, Hunyuan3D, Sketchfab e AssetHub.
- Licença e estado do Unity MCP (IvanMurzak) e dos MCPs de Unreal.

## 7. Fontes

- https://x.com/Stefan_3D_AI/status/2102110035853922310 (via snippet)
- https://x.com/Stefan_3D_AI/status/2104558611968229776 (via snippet)
- https://x.com/Stefan_3D_AI/status/2109643581787095115 (via snippet)
- https://github.com/witnesstodark/mr-mak-workspace
- https://github.com/ahujasid/blender-mcp
- https://github.com/lovecatisgood-sudo/3d-asset-generation-blender-unity-game-development-skills
- https://www.wesleychong.com/articles/ai-3d-game-72-hours-assethub-claude-code-unreal-mcp?lang=en
- https://github.com/IvanMurzak/Unity-MCP (via busca)
- https://www.linkedin.com/in/stefan-3d-ai/ (só snippet; fetch falhou)
- https://www.youtube.com/@stefan_3d_ai/videos (fetch sem conteúdo útil)
