# Checklist da página da loja (Acesso Antecipado)

Marque na ordem. Itens com (Will) dependem do dono. Rascunho dos textos em `textos_loja.md`.

## Conta e app
- [ ] (Will) Conta Steamworks, taxa do app paga, documentos fiscais e bancários.
- [ ] (Will) App ID criado; registrar em `integracao_godotsteam.md`.
- [ ] Depots Windows (e Linux, se for oferecer) e branch `default` de teste.

## Página da loja
- [ ] Nome: Ecos dos Estilhaços.
- [ ] Descrição curta (até 300 caracteres) e longa, em português do Brasil e em inglês.
- [ ] Gênero/tags: ação roguelike, 2D, top-down, single-player, fantasia sombria, indie.
- [ ] Cápsulas (header 460x215, small 231x87, main 616x353, vertical 374x448, library 600x900/ hero 3840x1240, logo) — arte nova passa pela revisora antes do dono.
- [ ] 5 capturas de tela 1920x1080 (use `captura_2d.gd`) e um trailer curto (opcional no início, recomendado).
- [ ] Classificação etária (questionário IARC no Steamworks) e conteúdo: violência fantasiosa.
- [ ] Requisitos mínimos/recomendados (medir no build: RAM, GPU, disco).
- [ ] Idiomas: interface em pt-BR; inglês antes do lançamento amplo.
- [ ] Aviso de Acesso Antecipado: o que está pronto (Região 1), o que vem (Região 2 fica fora), prazo estimado e preço previsto.
- [ ] Data de "Coming Soon" publicada pelo menos 2 semanas antes (regra de revisão da Steam: página pública antes do lançamento).

## Jogo
- [ ] Conquistas criadas no Steamworks com as mesmas API Names de `conquistas.csv`, com ícones 256x256 (normal e cinza).
- [ ] Nuvem: Auto-Cloud configurado e testado (ver integração).
- [ ] Build de lançamento: export Windows pelo `tools/build/build_2d.sh`, teste em máquina limpa, sem `steam_appid.txt`.
- [ ] Menu de opções, tutorial e remapeamento verificados no build exportado (teclado; controle é bônus).
- [ ] Revisão do Steam (build e página) — pedir com antecedência, leva alguns dias úteis.

## Antes de apertar o botão
- [ ] Checar texto da loja, preço e região; rever o aviso de Acesso Antecipado.
- [ ] Plano de patch: correção rápida nos primeiros dias, nota de versão em pt-BR.
