# Animação com IA + Blender para Echoes of the Shatter

Data da pesquisa: 2026-10-16. Nada foi baixado, instalado ou executado.
Legenda: **[V]** = visto em fonte consultada nesta pesquisa; **[I]** = inferência minha (não verificada).

## Resumo

- Melhor candidato de IA para o caso do jogo: **NVIDIA Kimodo (checkpoint SOMA)**. A página do modelo diz "pronto para uso comercial" (licença NVIDIA Open Model) [V], 282M de parâmetros [V], e dá para rodar em 8 GB movendo o codificador de texto para a CPU (menos de 3 GB de VRAM, mais lento) [V].
- **HY-Motion (Hunyuan) está descartado**: pede 24-26 GB de VRAM [V] e a licença exclui UE, Reino Unido e Coreia do Sul [V], mercados relevantes da Steam.
- **Tudo que depende de SMPL (MDM, MoMask, MotionGPT, T2M-GPT) tem risco de licença comercial**: o modelo SMPL é só não comercial; uso comercial exige licença da Meshcapade/Max Planck [V].
- Texto-para-movimento dá **rascunho**, não golpe final. Para golpes estilizados de chibi, a base mais segura continua sendo Mixamo + pacote CC0 + ajuste manual/procedural no Blender [I].

## 1. Modelos texto-para-movimento

| Modelo | Licença / uso comercial | VRAM | Saída | Qualidade p/ golpes estilizados | Converter p/ humanoide genérico |
|---|---|---|---|---|---|
| **Kimodo (NVIDIA, 2026)** | Código Apache-2.0; pesos: maioria "NVIDIA Open Model" (página do SOMA-RP-v1.2 diz pronto para uso comercial); checkpoint SMPLX-RP usa "NVIDIA R&D Model" (evitar) [V] | ~17 GB tudo na GPU; <3 GB com `TEXT_ENCODER_DEVICE=cpu` [V] | NPZ; SOMA 30 juntas, rotações a 30 fps; SMPL-X em NPZ AMASS; G1 em CSV [V]. BVH só SOMA, via nó ComfyUI de terceiros [V]; o repo não cita BVH [V] | Treinado em ~700 h de mocap "comercialmente amigável" [V fonte secundária]. Golpes exagerados: [I] mediana | Esqueleto SOMA é humanoide; mapear para o Humanoid da Unity via Blender é viável [I]. Windows: "deve funcionar, melhor com Docker" [V] |
| **HY-Motion 1.0 / Lite (Tencent)** | Licença Comunitária própria: **exclui UE, Reino Unido e Coreia do Sul**; acima de 1 milhão de MAU precisa pedir licença à Tencent; Tencent não reivindica direitos sobre saídas, mas proíbe usar saídas para treinar outros modelos [V] | 26 GB (1.0B) / 24 GB (Lite 0.46B) [V] | Esqueleto SMPL-H (fonte secundária) [V parcial]; README não documenta o formato [V] | Alta, mas inviável aqui | Inviável nesta máquina e bloqueado por licença [V] |
| **MoMask** | Código MIT; depende de SMPL/SMPL-X/PyTorch3D e datasets com licenças próprias [V] | Não informado; demo web roda em CPU [V] | **BVH direto**, juntas .npy, MP4 [V] | Movimentos simples tipo HumanML3D; golpes de fantasia fracos [I] | Fácil via BVH + Blender [V/I]. Risco: HumanML3D/AMASS com termos não comerciais [I, verificar] |
| **MDM** | Código MIT; CLIP, SMPL, PyTorch3D com licenças próprias [V] | Exige GPU CUDA, ~0,4 s/amostra; sem número de VRAM [V]; leve [I] | Posições XYZ (.npy), malha SMPL (.obj) e parâmetros SMPL; máx. 9,8 s [V]. Sem BVH nativo | Básica, vocabulário limitado [I] | Passo extra de posições/SMPL para BVH [I]; SMPL = não comercial [V] |
| **MotionGPT / T2M-GPT** | Licença não verificada; código acadêmico com mesma dependência de HumanML3D/SMPL [I] | Modelos pequenos, cabem em 8 GB [I] | Joints/SMPL [I] | Semelhante a MDM/MoMask [I] | Mesmo caminho e mesmo risco [I] |
| **OpenT2M (mar/2026)** | Dataset/benchmark aberto; licença não conferida [V parcial] | n/d | n/d | n/d | Só para acompanhar [I] |

O Kimodo também tem variantes G1 (robô) e SMPL-X; só o **SOMA** interessa [I].

### Licença do SMPL (ponto crítico)
O modelo SMPL permite só pesquisa, educação ou projetos artísticos **não comerciais**; incorporar em produto comercial é proibido e exige licença comercial via Meshcapade (smpl@max-planck-innovation.de) [V]. Não foi resolvido se animações geradas por modelos treinados com AMASS/HumanML3D carregam restrição [I]. Recomendação: evitar SMPL para o que for ao jogo, ou obter parecer jurídico.

## 2. Ferramentas do Blender

| Ferramenta | Custo / licença | O que faz | Observações |
|---|---|---|---|
| **Retarget** (KBS, extensions.blender.org) v5.2.0 | Grátis, GPL-3.0+, 220 KB [V] | Retarget, conversão Rigify "game-friendly", adicionar osso raiz, transferir root motion, bake [V] | Exige **Blender 5.0+** [V] |
| **Rokoko Studio Live for Blender** | Grátis; repo LGPL-3.0 (badge diz MIT: inconsistente) [V] | Retarget com mapeamento automático de ossos e "Auto Scale" [V] | Blender 2.80+ [V]; baixa bibliotecas na instalação [V]; guia diz que pede conta grátis e custa $0 [V fonte secundária]; pode atrasar em versões novas do Blender [V] |
| **Rigify** | Incluído no Blender | Rig procedural com IK/FK; útil para animar à mão golem, fantasma, quadrúpede | Para exportar à Unity, usar rig game-friendly [I] |
| **Auto-Rig Pro** | Pago (só comparação) | Retarget e export Unity mais confiáveis [V fonte secundária] | Não necessário |
| **FreeMoCap** | **AGPL**; uso comercial pode exigir licença negociada [V] | Mocap por vídeo | Risco de licença [V]; não é necessário |
| **RTMPose/MMPose** | Apache-2.0 (pesos sem declaração separada) [V] | Pose 2D/3D por vídeo | Não achei conversor pronto vídeo->BVH no Windows [V]; seria script próprio [I] |
| Conversores SMPL->FBX | Dependem do SMPL (não comercial) [V] | n/d | Não recomendado |

## 3. Caminho recomendado

**Principal (grátis, licença mais limpa):**
1. Gerar com **Kimodo SOMA-RP-v1.2**, com `TEXT_ENCODER_DEVICE=cpu` por causa dos 8 GB.
2. Exportar NPZ -> BVH (nó ComfyUI "Kimodo Motion Bridge" de terceiros ou script próprio) [V parcial].
3. Importar BVH no Blender (importador nativo).
4. Retarget para o rig Humanoid do jogo (Retarget KBS ou Rokoko); limpar escala, pés, osso raiz, bake.
5. Exportar FBX (Apply Transform, sem leaf bones) [I].
6. Unity: Rig > Animation Type = Humanoid, usar o avatar do personagem [I].

**Reserva:**
- Mixamo + pacote CC0, com ajustes no Blender (fonte confiável de golpes, já planejada).
- MoMask para rascunhos (BVH direto), só se a questão SMPL/AMASS for resolvida.
- Animação manual com Rigify + keyframes/procedural (essencial para golem, fantasma e cão quadrúpede).

**O que instalar:**

| Item | URL | Tamanho |
|---|---|---|
| Blender 5.x | https://www.blender.org/download/ | ~400 MB [I] |
| Retarget (KBS) | https://extensions.blender.org/add-ons/retarget/ | 220 KB [V] |
| Rokoko Studio Live Blender (opcional) | https://github.com/Rokoko/rokoko-studio-live-blender | ~1 MB + libs [I] |
| Kimodo (código) | https://github.com/nv-tlabs/kimodo | pequeno [I] |
| Pesos Kimodo-SOMA-RP-v1.2 | https://huggingface.co/nvidia/Kimodo-SOMA-RP-v1.2 | ~1-2 GB + codificador de texto de vários GB [I] |
| Python 3.10+ e PyTorch CUDA | python.org / pytorch.org | ~3 GB [I] |

Tudo em `D:\openclaude` (C: cheio).

## 4. Riscos e ajustes manuais

| Risco | Detalhe |
|---|---|
| Licença SMPL | Não comercial; evitar MDM/MoMask/MotionGPT/T2M-GPT em produção sem licença [V] |
| Licença Hunyuan | Exclui UE, UK e Coreia [V] |
| Licença Kimodo | Pesos Open Model declarados comerciais pela NVIDIA; ler o texto completo antes do lançamento; evitar checkpoint SMPLX R&D [V] |
| FreeMoCap | AGPL [V] |
| Proporção chibi | Cabeça grande e pernas curtas: mocap de proporção realista causa pés deslizando, braços atravessando o corpo, passadas longas. Ajustar passada, reduzir amplitude, refazer IK de pés [I] |
| Golpes estilizados | Modelos tendem a movimento natural; antecipação, impacto e hold frames exagerados são manuais [I] |
| Inimigos não humanos | Golem, fantasma e cão quadrúpede não são cobertos por modelos humanos; usar Rigify, curvas e ruído procedural [I] |
| Root motion e loop | Corrigir deslocamento, fechar loops de idle/caminhada, definir osso raiz [I] |
| Infra | Kimodo sem suporte oficial a Windows; talvez precise de Docker/WSL (instalação extra) [V] |
| Blender->Unity | Relato de dedos/pernas deformados em export; conferir pose de repouso e escala [V fonte secundária] |

## Fontes

- HY-Motion README: https://github.com/Tencent-Hunyuan/HY-Motion-1.0
- Licença HY-Motion: https://huggingface.co/tencent/HY-Motion-1.0/blob/main/LICENSE.txt
- HY-Motion paper: https://arxiv.org/abs/2512.23464
- Kimodo repo: https://github.com/nv-tlabs/kimodo
- Kimodo SOMA v1.2: https://huggingface.co/nvidia/Kimodo-SOMA-RP-v1.2
- Kimodo (notícia): https://rits.shanghai.nyu.edu/ai/nvidia-releases-kimodo-controllable-text-to-motion-for-characters-and-humanoid-robots/
- Kimodo BVH (ComfyUI): https://comfy.icu/node/Kimodo_ExportBVH
- SMPL licença: https://smpl.is.tue.mpg.de/modellicense.html
- MoMask: https://github.com/EricGuo5513/momask-codes
- MDM: https://github.com/GuyTevet/motion-diffusion-model
- OpenT2M: https://arxiv.org/abs/2603.18623
- Retarget (KBS): https://extensions.blender.org/add-ons/retarget/
- Rokoko Blender: https://github.com/Rokoko/rokoko-studio-live-blender
- Guia Rokoko: https://www.blendernation.com/2021/12/23/retargeting-using-rokoko-complete-guide/
- Retarget para Rigify: https://www.blendernation.com/2023/01/14/the-simplest-way-to-retarget-mocap-to-a-rigify-rig-free-and-easy
- FreeMoCap: https://pypi.org/project/freemocap/1.0.34/
- MMPose: https://pypi.org/project/mmpose/
