using Echoes.Core;
using Echoes.Gameplay;
using UnityEngine;

namespace Echoes.Presentation
{
    /// <summary>
    /// Liga a máquina de entrada do ataque básico (<see cref="BasicInputEvent"/>, docs/18 seção 1.3) aos VFX de carga e de defesa.
    /// Fica separado para o resto do presenter não depender do evento: sem este arquivo o projeto compila do mesmo jeito.
    /// A defesa comum e a perfeita ainda não têm evento (o core só avisa GuardUp e GuardDown); ver <c>GuardBlock</c> e <c>GuardPerfect</c>.
    /// </summary>
    public sealed partial class SkillVfxPresenter
    {
        partial void SubscribeBasicInput(EventBus events)
        {
            events.Subscribe<BasicInputEvent>(OnBasicInput);
            events.Subscribe<GuardBlockEvent>(OnGuardBlock);
        }

        partial void UnsubscribeBasicInput(EventBus events)
        {
            events.Unsubscribe<BasicInputEvent>(OnBasicInput);
            events.Unsubscribe<GuardBlockEvent>(OnGuardBlock);
        }

        // Golpe absorvido pela defesa: faisca comum, ou clarao da defesa perfeita. O contato fica na frente do defensor, virado para o atacante.
        void OnGuardBlock(in GuardBlockEvent evt)
        {
            if (evt.Target == null) return;
            var targetPos = evt.Target.Position;
            var toAttacker = evt.Attacker != null ? (evt.Attacker.Position - targetPos).NormalizedOr(evt.Target.Forward) : evt.Target.Forward;
            var contact = new Vector3(targetPos.X + toAttacker.X * 0.7f, 0f, targetPos.Z + toAttacker.Z * 0.7f);
            if (evt.Target.Owner is Component owner && owner != null) contact.y = owner.transform.position.y;
            contact.y += 1f;
            if (evt.Perfect) GuardPerfect(evt.Target, contact);
            else GuardBlock(evt.Target, contact);
        }

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
