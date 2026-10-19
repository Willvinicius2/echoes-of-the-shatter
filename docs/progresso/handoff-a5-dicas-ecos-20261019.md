# Passagem de bastão: A5, dicas do Guardião pelos Ecos (19/10)
- Feito: aviso no chão dos golpes do Guardião com Eco só aparece depois do Eco (gate `TelegraphHints`), faixa com a dica ao recolher o Eco, teste `TelegraphHints_HideTheGuardianStrikeUntilItsEchoIsFound`. Detalhes em `docs/design/21_roteiro_regiao1.md` (seção "Dicas do golpe do Guardião").
- Não validado: `checar_cliente.sh` não rodou na nuvem (sem dotnet); vale o CI `cliente.yml`. Falta conferir no editor (A2).
- Atenção: sem nenhum Eco o chefe fica ilegível no chão; ajuste em `echoes.csv` (minToReveal) ou zere o gate.
