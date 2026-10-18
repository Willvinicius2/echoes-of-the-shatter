# Validador de dados (`tools/dados/validate_data.py`)

Valida as tabelas CSV do ContentDB, os fixtures de teste e os saves JSON. Usa só a biblioteca padrão do Python 3 (testado com Python 3.14, no PATH). Não precisa instalar nada.

Formato das tabelas, convenção de IDs e política de migração: `docs/tecnico/06_dados.md`.

## Como rodar

A partir da raiz do repositório (`D:\openclaude\EchoesOfTheShatter`):

```
python tools/dados/validate_data.py                     # conteúdo real: EchoesOfTheShatter/Content/Data
python tools/dados/validate_data.py --self-test         # tudo: conteúdo real, fixtures válidos, inválidos, saves e migração
python tools/dados/validate_data.py --data OUTRA_PASTA  # valida outra pasta de CSV (pode repetir --data)
python tools/dados/validate_data.py --data X --expect-fail   # passa só se X tiver erro (testes negativos)
python tools/dados/validate_data.py --save slot_1.json --content EchoesOfTheShatter/Content/Data
python tools/dados/validate_data.py --update-lock       # grava content_lock.json: só na primeira release
```

Outras opções: `--schemas PASTA` (esquemas diferentes), `--quiet` (omite as linhas `info`).

Código de saída: `0` tudo certo, `1` erro de dados, `2` erro de uso ou esquema ausente.

## O que o `--self-test` faz

1. Valida `EchoesOfTheShatter/Content/Data` (o conteúdo real). Precisa passar.
2. Valida `ShatterCore/tests/data` (fixtures válidos). Precisa passar.
3. Para cada pasta em `ShatterCore/tests/data/invalid/<caso>/`, valida e confere se falha com o erro de `expected_error.json` (`table`, `line`, `code`). Se o erro esperado não aparecer, o teste falha.
4. Valida os saves em `ShatterCore/tests/data/saves/` (válidos) e `saves/invalid/` (devem falhar).
5. Roda a migração de referência v1 para v2 e compara com `saves/migration/v1_to_v2_expected.json`.

## Adicionar ou mudar uma tabela

- Esquema em `EchoesOfTheShatter/Content/Data/schemas/<tabela>.schema.json` (formato `shatter-table-schema/1`). Cada tabela CSV precisa de um esquema, e cada esquema precisa de um CSV. Um CSV sem esquema é `E_UNKNOWN_TABLE`, e um esquema sem CSV é `E_MISSING_TABLE`.
- Listas de valores comuns ficam em `schemas/_enums.json` e são referenciadas com `@nome`.
- Cabeçalho do CSV = nomes das colunas do esquema, na mesma ordem. Qualquer diferença é `E_HEADER`.

## Adicionar um fixture inválido

Crie `ShatterCore/tests/data/invalid/<nome>/` com as 15 tabelas (cópias do fixture válido com um defeito) e um `expected_error.json`:

```json
{"table": "skills.csv", "line": 4, "code": "E_DUP_ID"}
```

`line` é a linha 1-based do arquivo (a 1 é o cabeçalho). Use um defeito por caso, para que o código esperado seja o único motivo de falha.

## Save

Envelope `{format, save_version, sha256, data}`, com esquema em `schemas/save_v<N>.schema.json` (`x-save-version` marca a versão). O validador confere o SHA-256 da forma canônica de `data`, o esquema e as regras semânticas (uids, afixos por raridade, IDs existentes, expedição, regras de IA). Versão de save sem esquema é `E_TOO_NEW`.

## Códigos de erro mais comuns

| Código | Significado |
|---|---|
| `E_HEADER` | Cabeçalho do CSV diferente do esquema |
| `E_COLUMNS` | Número de colunas errado na linha (vírgula decimal também cai aqui) |
| `E_TYPE`, `E_RANGE`, `E_ENUM` | Valor com tipo, faixa ou enum errados |
| `E_DUP_ID` | ID ou chave primária repetida |
| `E_FK` | Referência a um ID que não existe na tabela de destino |
| `E_REQUIRED` | Coluna obrigatória vazia |
| `E_QUOTE` | Aspas no CSV (texto livre não entra nas tabelas) |
| `E_IDLE`, `E_WEAPON`, `E_EFFECT`, `E_LOOT`, `E_ENEMY`, `E_BOSS`, `E_CLASS` | Regras entre colunas (ver `docs/tecnico/06_dados.md`, seção 4) |
| `E_CHECKSUM`, `E_SCHEMA`, `E_SAVE` | Save: hash, esquema e regra semântica |
| `E_ID_REMOVED`, `E_VERSION` | Conteúdo publicado: ID sumiu, ou dados mudaram sem subir `content_version` |

Avisos (`AVISO`) não reprovam a validação. Os erros, sim.

## Limites conhecidos

- O validador confere o formato dos IDs de `skills`, `loot`, `maps` e outros, mas só confere a existência quando a tabela de destino existe. Veja as pendências P2, P3 e P5 em `docs/tecnico/06_dados.md`.
- A checagem de localização (`Loc/`) só roda se a pasta existir. Pendência P6.
- O `--self-test` é o que cobre os fixtures. Rodar só o modo padrão não os valida. Pendência P7.
