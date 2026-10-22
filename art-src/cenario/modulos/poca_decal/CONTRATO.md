# Contrato das partes (poca_decal)
Cada parte é um arquivo `def build(L, ...)` com `L = lib.contexto("A"|"B"|"C")`; só edita o seu arquivo.
Arrays float32 HxW (H=L.H, W=L.W), linha 0 = topo.

- `mascara.py`  build(L) -> dict(wet, water, signed)
  - `water` 0..1: região de água parada, borda nítida e antialiased (1 px), contorno irregular em degraus de laje (C), sem círculos de desenho.
  - `wet` 0..1: umidade do piso: vale ~1 junto à água e decai para fora com largura VARIÁVEL (2–15 cm, mais larga onde escorre), seguindo juntas (linhas retas de laje em 2 ângulos, filetes finos de umidade de 1–3 cm entrando nas frestas, até 30–60 cm), sem anel uniforme. `wet >= water` sempre.
  - `signed`: distância assinada em metros (>0 fora da água, <0 dentro).
- `bordas.py`  build(L, m) -> dict(rgba, altura)   (m = saída de mascara.build)
  - `rgba` HxWx4 (cor linear sRGB 0..1, alfa 0..1): lama fina, cascalho miúdo variado (grãos de 1–6 mm, poucos de 1–2 cm) junto à borda e nos filetes, fiapos/folhas de musgo realistas (fitas curvas finas de 2–12 mm de largura, tons verde-escuro a oliva, com variação), NENHUM anel escuro grosso, nenhuma mancha lisa.
  - `altura` 0..1 relevo dos grãos e fiapos (0.5 = neutro).
- `gotas.py`  build(L, m) -> dict(altura)  
  - `altura` HxW em metros (~±1 mm) da superfície da água dentro de `water`: ondulação fina e irregular (não círculos concêntricos de desenho) mais 1–3 gotas com 2–3 anéis pequenos e sutis; 0 fora da água.
  - além disso escreve `godot/art/shaders/cripta_gotas.gdshader` (quad transparente animado: anéis pequenos que nascem e somem em pontos aleatórios, alfa só nos anéis) e `godot/art/materials/M_Cripta_Gotas.tres`.

`compose.py` (dono: thread principal) junta tudo em `T_Poca_<V>_albedo.png`, `_orm.png`, `_n.png`, o Decal `.tscn`, e renderiza a prancha.
Cada arquivo traz `if __name__ == "__main__":` que salva uma prévia PNG em /tmp/poca_<parte>_<V>.png. Python: /tmp/venv/bin/python (numpy, scipy, PIL).
Qualidade: realismo pintado de jogo, sem formas geométricas óbvias. Itere olhando as prévias (Read no PNG) pelo menos 4 vezes.
