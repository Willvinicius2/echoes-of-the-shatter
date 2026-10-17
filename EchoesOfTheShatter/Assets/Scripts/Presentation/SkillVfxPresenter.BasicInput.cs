using Echoes.Core;
using Echoes.Gameplay;

namespace Echoes.Presentation
{
    /// <summary>
    /// Liga a máquina de entrada do ataque básico (<see cref="BasicInputEvent"/>, docs/18 seção 1.3) aos VFX de carga e de defesa.
    /// Fica separado para o resto do presenter não depender do evento: sem este arquivo o projeto compila do mesmo jeito.
    /// A defesa comum e a perfeita ainda não têm evento (o core só avisa GuardUp e GuardDown); ver <c>GuardBlock</c> e <c>GuardPerfect</c>.
    /// </summary>
    public sealed partial class SkillVfxPresenter
    {
        partial void SubscribeBasicInput(EventBus events) => events.Subscribe<BasicInputEvent>(OnBasicInput);

        partial void UnsubscribeBasicInput(EventBus events) => events.Unsubscribe<BasicInputEvent>(OnBasicInput);

        void OnBasicInput(in BasicInputEvent evt)
        {
            switch (evt.Kind)
            {
                case BasicInputKind.ChargeStarted:
                    BeginCharge(evt.Owner, evt.Skill != null ? evt.Skill.Id : string.Empty);
                    break;
                case BasicInputKind.ChargeFull:
                    ChargeFull(evt.Owner, evt.Skill != null ? evt.Skill.Id : string.Empty);
                    break;
                case BasicInputKind.ChargeCancelled:
                case BasicInputKind.HeavyReleased:
                    EndCharge(evt.Owner);
                    break;
                case BasicInputKind.GuardUp:
                    GuardUp(evt.Owner);
                    break;
                case BasicInputKind.GuardDown:
                    GuardDown(evt.Owner);
                    break;
                case BasicInputKind.GuardBroke:
                    GuardBroke(evt.Owner);
                    break;
            }
        }
    }
}
