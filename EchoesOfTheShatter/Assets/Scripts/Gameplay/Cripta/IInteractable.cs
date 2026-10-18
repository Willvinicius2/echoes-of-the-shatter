using UnityEngine;

namespace Echoes.Gameplay
{
    /// <summary>
    /// Objeto da Cripta que o herói aciona com a ação Interagir (RF-64, tecla F remapeável): baú e alavanca do atalho. A UI mostra o aviso
    /// "[F] ..." do mais próximo dentro do alcance e chama <see cref="Interact"/> ao apertar.
    /// </summary>
    public interface IInteractable
    {
        /// <summary>Ainda pode ser usado (baú fechado, alavanca não usada)?</summary>
        bool CanInteract { get; }

        /// <summary>Chave de Loc do aviso (ex.: ui.interact.open_chest).</summary>
        string PromptKey { get; }

        Vector3 Position { get; }

        /// <summary>Alcance, em metros (técnico).</summary>
        float Reach { get; }

        void Interact();
    }
}
