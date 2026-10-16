using UnityEngine;

namespace Echoes.Presentation
{
    /// <summary>
    /// Fica na raiz do prefab pintado (o GameObject do Animator): os eventos de clipe (AnimationEvent) chamam <see cref="OnClipEvent"/> aqui e
    /// o evento segue para o <see cref="PresentationController"/> da entidade (o pai). Só repassa; não decide nada.
    /// </summary>
    [DisallowMultipleComponent]
    public sealed class AnimationEventRelay : MonoBehaviour
    {
        PresentationController target;

        // Chamado pelo Animator (nome da função gravado no clipe: ver EchoesAnimationImport.EventFunction).
        public void OnClipEvent(string clipEvent)
        {
            if (target == null) target = GetComponentInParent<PresentationController>();
            if (target != null) target.HandleClipEvent(clipEvent);
        }
    }
}
