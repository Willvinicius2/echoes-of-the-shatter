using System.IO;
using UnityEngine;
using UnityEngine.InputSystem;

namespace Echoes.Gameplay
{
    /// <summary>
    /// Lê o Input System pelas ações nomeadas do <c>Echoes.inputactions</c> (RF-64, RF-65). Carrega o
    /// remapeamento salvo em <c>persistentDataPath/bindings.json</c> (docs/04_arquitetura.md, seção 8).
    /// Leitura por polling no Update (sem callbacks, sem alocação por quadro).
    /// </summary>
    /// <summary>Fonte de entrada roteirizada (gravação de vídeo e testes): mesma forma que o teclado e o mouse entregam.</summary>
    public interface IScriptedInput
    {
        Vector2 Move { get; }
        Vector2 Aim { get; }
        bool WasPressed(HeroCommand command);
        bool IsHeld(HeroCommand command);
    }

    [DefaultExecutionOrder(-950)]
    [DisallowMultipleComponent]
    public sealed class PlayerInputHandler : MonoBehaviour
    {
        const string BindingsFile = "bindings.json";

        [Tooltip("Assets/Settings/Echoes.inputactions")]
        [SerializeField] InputActionAsset actions;
        [SerializeField] bool loadSavedBindings = true;

        InputActionMap map;
        InputAction move;
        InputAction aim;
        InputAction pause;
        InputAction interact;
        InputAction inventory;
        InputAction worldMap;
        InputAction passiveTree;
        readonly InputAction[] commandActions = new InputAction[InputActionNames.ByCommand.Length];

        public bool IsReady => map != null;
        public InputActionAsset Actions => actions;

        public const string PreloadedActionsName = "Echoes";
        const string DefaultActionsPath = "Assets/Settings/Echoes.inputactions";

        void Awake()
        {
#if UNITY_EDITOR
            // O asset de acoes nao serializa a referencia nas cenas montadas por script (fileID 0); no editor carrega pelo caminho.
            if (actions == null) actions = UnityEditor.AssetDatabase.LoadAssetAtPath<InputActionAsset>(DefaultActionsPath);
#endif
            // Player: o Echoes.inputactions entra no build pelos Preloaded Assets (Echoes.EditorTools.Build); as cenas montadas por script nao
            // serializam a referencia, entao procura o asset ja carregado pelo nome.
            if (actions == null)
            {
                foreach (var loaded in Resources.FindObjectsOfTypeAll<InputActionAsset>())
                {
                    if (loaded.name == PreloadedActionsName) actions = loaded;
                }
            }
            if (actions == null)
            {
                Debug.LogError("[Input] Ligue o Echoes.inputactions no PlayerInputHandler.", this);
                enabled = false;
                return;
            }
            if (loadSavedBindings) LoadBindingOverrides();

            map = actions.FindActionMap(InputActionNames.Map, true);
            move = map.FindAction(InputActionNames.Move, true);
            aim = map.FindAction(InputActionNames.Aim, true);
            pause = map.FindAction(InputActionNames.Pause, false);
            interact = map.FindAction(InputActionNames.Interact, false);
            inventory = map.FindAction(InputActionNames.Inventory, false);
            worldMap = map.FindAction(InputActionNames.WorldMap, false);
            passiveTree = map.FindAction(InputActionNames.PassiveTree, false);
            for (var i = 0; i < commandActions.Length; i++)
                commandActions[i] = map.FindAction(InputActionNames.ByCommand[i], true);
        }

        void OnEnable()
        {
            map?.Enable();
        }

        void OnDisable()
        {
            map?.Disable();
        }

        /// <summary>Entrada roteirizada (modo de gravação -record). Nula no jogo normal; quando existe, substitui o teclado e o mouse.</summary>
        public IScriptedInput Script { get; set; }

        /// <summary>WASD no espaço da tela (x = direita, y = para cima), módulo até 1.</summary>
        public Vector2 Move => Script != null ? Vector2.ClampMagnitude(Script.Move, 1f) : move != null ? Vector2.ClampMagnitude(move.ReadValue<Vector2>(), 1f) : Vector2.zero;

        /// <summary>Posição do ponteiro em pixels de tela.</summary>
        public Vector2 AimScreenPosition => Script != null ? Script.Aim : aim != null ? aim.ReadValue<Vector2>() : Vector2.zero;

        public bool WasPressed(HeroCommand command)
        {
            if (Script != null) return Script.WasPressed(command);
            var action = ActionFor(command);
            return action != null && action.WasPressedThisFrame();
        }

        public bool IsHeld(HeroCommand command)
        {
            if (Script != null) return Script.IsHeld(command);
            var action = ActionFor(command);
            return action != null && action.IsPressed();
        }

        /// <summary>Interagir (RF-64, remapeavel; padrao F): falar com Ilsa e Tico.</summary>
        public bool InteractPressed => interact != null && interact.WasPressedThisFrame();

        /// <summary>Glifo da tecla de Interagir para os prompts (vem do Input System: acompanha o remapeamento).</summary>
        public string InteractGlyph => interact != null ? interact.GetBindingDisplayString() : "F";

        public bool PausePressed => pause != null && pause.WasPressedThisFrame();
        public string InventoryGlyph => inventory != null ? inventory.GetBindingDisplayString() : "I";

        public bool InventoryPressed => inventory != null && inventory.WasPressedThisFrame();
        public bool MapPressed => worldMap != null && worldMap.WasPressedThisFrame();
        public bool PassiveTreePressed => passiveTree != null && passiveTree.WasPressedThisFrame();

        /// <summary>Texto da tecla atual para a UI (vem do Input System, não do código).</summary>
        public string GetBindingDisplay(HeroCommand command)
        {
            var action = ActionFor(command);
            return action != null ? action.GetBindingDisplayString() : string.Empty;
        }

        public void SaveBindingOverrides()
        {
            if (actions == null) return;
            var path = Path.Combine(Application.persistentDataPath, BindingsFile);
            File.WriteAllText(path, actions.SaveBindingOverridesAsJson());
        }

        void LoadBindingOverrides()
        {
            var path = Path.Combine(Application.persistentDataPath, BindingsFile);
            if (!File.Exists(path)) return;
            try
            {
                actions.LoadBindingOverridesFromJson(File.ReadAllText(path));
            }
            catch (System.Exception e)
            {
                Debug.LogWarning($"[Input] Remapeamento salvo ignorado ({e.Message}).", this);
            }
        }

        InputAction ActionFor(HeroCommand command)
        {
            var index = (int)command;
            return index >= 0 && index < commandActions.Length ? commandActions[index] : null;
        }
    }
}
