extends RefCounted
## Gravação segura dos saves do cliente 2D (árvore de passivos, fases vencidas, opções, conquistas).
## Grava primeiro em `<arquivo>.tmp` e só depois troca pelo arquivo de verdade: se o jogo fechar ou a energia cair no
## meio da gravação, o save anterior continua inteiro. O save do meta já é gravado assim pelo core.

const SUFIXO := ".tmp"

## Grava o texto em `caminho`. Retorna false se não deu para gravar (o arquivo anterior fica como estava).
static func gravar(caminho: String, texto: String) -> bool:
	var tmp := caminho + SUFIXO
	var f := FileAccess.open(tmp, FileAccess.WRITE)
	if f == null:
		return false
	f.store_string(texto)
	var ok := f.get_error() == OK
	f.close()
	if not ok:
		DirAccess.remove_absolute(tmp)
		return false
	return DirAccess.rename_absolute(tmp, caminho) == OK

## Texto de `caminho`, ou "" se não existe. Se a troca foi interrompida (só o `.tmp` ficou), lê o `.tmp`.
static func ler(caminho: String) -> String:
	if FileAccess.file_exists(caminho):
		return FileAccess.get_file_as_string(caminho)
	if FileAccess.file_exists(caminho + SUFIXO):
		return FileAccess.get_file_as_string(caminho + SUFIXO)
	return ""

static func existe(caminho: String) -> bool:
	return FileAccess.file_exists(caminho) or FileAccess.file_exists(caminho + SUFIXO)
