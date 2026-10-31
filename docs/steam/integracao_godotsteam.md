# Integração com a Steam (GodotSteam)

Responsável: setor D (doc 27, seção 11). Código: `godot/scripts2d/steam_2d.gd`. O jogo funciona sem a Steam: sem o plugin, sem o cliente aberto ou com a inicialização falhando, a interface vira no-op e as conquistas ficam num registro local (`user://steam_2d.json`), reenviadas quando a Steam estiver ativa.

## Como a interface funciona
- `Steam2D.iniciar()` procura o singleton `Steam` (GDExtension GodotSteam 4.x) e chama `steamInitEx()`. Todas as chamadas à API são dinâmicas (`call`), então o projeto compila sem o plugin instalado.
- `tick()` roda `run_callbacks()` a cada quadro (feito por `menus_2d.gd`).
- `evento("nome")` desbloqueia as conquistas ligadas ao evento em `godot/data2d/conquistas.csv` (`id`, `steam_id`, `evento`, `loc`). Para uma conquista nova: uma linha no CSV, os textos em `loc_2d.csv` e a mesma ID (API Name) no Steamworks.
- Eventos ligados hoje (em `menus_2d.gd`): `corrida_fim`, `vitoria`, `amuleto_criado`, `melhoria_comprada`. Eventos de combate (inimigos, chefe) pedem um ponto de ligação em `run_2d.gd`, que é de outro setor.

## Conquistas iniciais (rascunho; nomes e descrições em `loc_2d.csv`)
| ID local | API Name na Steam | Quando |
|---|---|---|
| primeira_corrida | ACH_FIRST_RUN | terminar a primeira corrida, vencendo ou não |
| cripta_vencida | ACH_CRYPT_CLEARED | vencer o Guardião |
| primeira_forja | ACH_FIRST_FORGE | criar o primeiro amuleto |
| primeira_melhoria | ACH_FIRST_UPGRADE | comprar a primeira melhoria permanente |

## Nuvem de saves
Usar o **Steam Auto-Cloud**, sem código: no Steamworks, em Application > Steam Cloud, configurar o diretório raiz do `user://` do Godot e o padrão dos arquivos `save_2d.json` e `opcoes_2d.json` (não incluir `steam_2d.json`, que é por máquina). Passos:
1. Definir `application/config/use_custom_user_dir=true` e `custom_user_dir_name="EcosDosEstilhacos"` no projeto de exportação, para o caminho ser estável (Windows: `%APPDATA%\EcosDosEstilhacos`).
2. Configurar o Auto-Cloud com esse caminho (raiz `WinAppDataRoaming`) e os padrões acima; cotas pequenas bastam (poucos KB).
3. Testar com duas contas/máquinas antes do lançamento. `Steam2D.nuvem_ativa()` diz se o cliente tem a nuvem ligada (para mostrar um aviso, se quisermos).

## Instalação do plugin (a fazer pelo dono ou pela thread de build)
1. Baixar o GodotSteam GDExtension compatível com o Godot 4.4.x (https://godotsteam.com) e colocar em `godot/addons/godotsteam/`.
2. Criar `steam_appid.txt` com o App ID do jogo (pendente: depende da conta Steamworks) ao lado do executável, só para desenvolvimento. Nunca no pacote final da Steam.
3. Atenção para o CI: o `build_2d.sh` monta um projeto só com o cliente 2D; copiar `addons/godotsteam` nele quando o plugin entrar. Sem o plugin o build continua válido.
4. Licenças: GodotSteam é MIT; o Steamworks SDK é redistribuído conforme o contrato do Steamworks.

## Pendências que dependem do dono
- Conta Steamworks e App ID (taxa de registro do app).
- Aprovar nomes e textos das conquistas e as artes (cápsulas) da loja.
