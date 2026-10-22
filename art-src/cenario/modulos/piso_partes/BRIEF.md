# Piso da Cripta — regras comuns das partes
Módulo 8x8 m periódico, topo das lajotas em z=0 (Blender, +Z cima). Layout em `comum.layout()` (43 lajotas retangulares,
já sem junta; junta = comum.JUNTA 4,5 cm). NÃO mude comum.py. Python: `python3 arquivo.py` (módulo bpy já instalado, headless).
Cada parte é UM arquivo em piso_partes/ com `construir() -> list[bpy.types.Object]` (cria objetos na cena atual, sem limpar
a cena, sem exportar) e um bloco `if __name__ == "__main__":` que limpa a cena, chama construir() e renderiza prévia
com `comum.previa(...)` em ../previas/piso/<parte>_*.png (duas ou três câmeras: 3/4 de jogo, rasante, close).
Referência visual: /mnt/project-files/referencias-cripta/terreno.png e /mnt/project-files/terreno_isolado_arena.png
(lajotas azul-ardósia escuras, quinas lascadas, rachaduras, poças com reflexo, sujeira e musgo nas juntas).
O Will REPROVOU visual de "massinha": arestas vivas e irregulares, chanfros desiguais, lascas, variação real de altura
e de tom por lajota, detalhe que se vê na câmera de jogo (~50° de inclinação, lajotas ocupam ~100 px). Nada de cubo liso perfeito.
Orçamento: parte < 60k triângulos. Sem texturas externas: cor sólida por material no .glb (materiais com nomes M_Piso_*),
nós procedurais só para a prévia. Determinístico (random.Random(seed fixo)). Cada material nomeado M_Piso_<algo>.
Ciclo: gere, renderize, OLHE a imagem (Read), corrija, repita pelo menos 3 vezes; só entregue quando parecer arte 3D de jogo bonita.
Skills do repo (.claude/skills): leia create-game-assets/SKILL.md (validação em contexto) e, se tocar em material, godot-shaders; diga no relatório quais usou.
Edite só o seu arquivo. Não faça commit. Responda curto: o que fez, caminho das prévias, contagem de triângulos, pendências.
