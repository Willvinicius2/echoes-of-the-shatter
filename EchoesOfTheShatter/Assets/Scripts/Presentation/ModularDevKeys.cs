using UnityEngine;
using UnityEngine.InputSystem;

namespace Echoes.Presentation
{
    /// <summary>
    /// Atalho de desenvolvimento para testar as pecas do heroi modular: F1 a F5 tiram e poem Head, Chest, Hands, Legs e Feet;
    /// F6 veste tudo (starter); F7 tira tudo (corpo nu). So no editor, em Development Build ou com o argumento -devkeys.
    /// </summary>
    [DisallowMultipleComponent]
    public sealed class ModularDevKeys : MonoBehaviour
    {
        [SerializeField] ModularCharacter modular;

        static readonly Key[] SlotKeys = { Key.F1, Key.F2, Key.F3, Key.F4, Key.F5 };

        void Awake()
        {
            if (modular == null) modular = GetComponentInChildren<ModularCharacter>();
            if (!Application.isEditor && !Debug.isDebugBuild && !DevKeysRequested()) enabled = false;
        }

        /// <summary>Na build de release as teclas ficam desligadas; o argumento -devkeys liga (para o dono testar as pecas sem Development Build).</summary>
        static bool DevKeysRequested()
        {
            foreach (var arg in System.Environment.GetCommandLineArgs())
                if (string.Equals(arg, "-devkeys", System.StringComparison.OrdinalIgnoreCase)) return true;
            return false;
        }

        void Update()
        {
            var keyboard = Keyboard.current;
            if (keyboard == null || modular == null) return;
            for (var i = 0; i < SlotKeys.Length; i++)
            {
                if (!keyboard[SlotKeys[i]].wasPressedThisFrame) continue;
                var slot = (HeroPartSlot)i;
                if (modular.IsEquipped(slot)) modular.Unequip(slot);
                else modular.Equip(slot, HeroPartCatalog.StarterSet);
            }
            if (keyboard[Key.F6].wasPressedThisFrame)
                for (var i = 0; i < SlotKeys.Length; i++) modular.Equip((HeroPartSlot)i, HeroPartCatalog.StarterSet);
            if (keyboard[Key.F7].wasPressedThisFrame)
                for (var i = 0; i < SlotKeys.Length; i++) modular.Unequip((HeroPartSlot)i);
        }
    }
}
