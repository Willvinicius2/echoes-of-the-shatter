using UnityEngine;

namespace Echoes.Gameplay
{
    /// <summary>
    /// Parede rachada (docs/14 seção 5.3): abre com um golpe de Investida, Fenda de Pedra ou Escudada do herói perto dela (não o Corte de
    /// Ferro). Os IDs de habilidade vêm do layout. Depois de aberta fica aberta (não volta ao checkpoint).
    /// </summary>
    public sealed class SecretWall : MonoBehaviour
    {
        [SerializeField] CombatSystemHost combatHost;
        [SerializeField] HeroController hero;
        [SerializeField] string secretId;
        [SerializeField] string[] opensWithSkillIds;
        [Tooltip("Distância máxima do herói até a parede para o golpe contar, em metros (técnico).")]
        [SerializeField, Min(0.5f)] float reach = 6f;

        bool subscribed;

        public bool IsOpen { get; private set; }
        public string SecretId => secretId;

        void Start()
        {
            var events = combatHost != null ? combatHost.Events : null;
            if (events == null) return;
            events.Subscribe<SkillPhaseEvent>(OnSkillPhase);
            subscribed = true;
        }

        void OnDestroy()
        {
            var events = combatHost != null ? combatHost.Events : null;
            if (subscribed && events != null) events.Unsubscribe<SkillPhaseEvent>(OnSkillPhase);
        }

        void OnSkillPhase(in SkillPhaseEvent evt)
        {
            if (IsOpen || evt.Skill == null || evt.Owner == null || evt.Owner.Team != CombatTeam.Hero) return;
            if (evt.Phase != ActionPhase.Impact && evt.Phase != ActionPhase.Recovery) return; // a Investida bate na chegada
            if (System.Array.IndexOf(opensWithSkillIds, evt.Skill.Id) < 0) return;
            var d = new Vector3(evt.Owner.Position.X, 0f, evt.Owner.Position.Z) - new Vector3(transform.position.x, 0f, transform.position.z);
            if (d.sqrMagnitude > reach * reach) return;
            Open();
        }

        public void Open()
        {
            if (IsOpen) return;
            IsOpen = true;
            gameObject.SetActive(false);
            var evt = new SecretOpenedEvent { SecretId = secretId };
            combatHost?.Events?.Publish(in evt);
        }
    }
}
