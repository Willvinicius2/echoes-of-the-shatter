using UnityEngine;

namespace Echoes.Gameplay
{
    /// <summary>
    /// Checkpoint da Cripta: o herói que passa dentro do raio fixa este ponto como o de retorno (RF-18, F-07). Ao fixar um ponto NOVO enche as
    /// poções pela regra do core (cinto do herói), publica <see cref="CheckpointReachedEvent"/> (a UI salva e avisa) e dá um pulso visual no
    /// marcador. Ao voltar depois da morte o core também enche as poções (Revive) e os inimigos mortos reaparecem (<see cref="EncounterDirector"/>).
    /// </summary>
    public sealed class CheckpointZone : MonoBehaviour
    {
        [SerializeField] CombatSystemHost combatHost;
        [SerializeField] HeroController hero;
        [Tooltip("Raio do ponto de ativação, em metros (técnico).")]
        [SerializeField, Min(0.5f)] float radius = 3f;
        [SerializeField] string checkpointId;
        [Tooltip("Duração do pulso visual ao ativar, em segundos (feedback F-07).")]
        [SerializeField, Min(0.05f)] float pulseSeconds = 0.6f;
        [Tooltip("Quanto o marcador cresce no pico do pulso (1 = nada).")]
        [SerializeField, Min(1f)] float pulseScale = 1.35f;

        float pulseLeft;
        Vector3 baseScale = Vector3.one;

        public string CheckpointId => checkpointId;

        void Awake()
        {
            baseScale = transform.localScale;
        }

        void Update()
        {
            if (pulseLeft > 0f)
            {
                pulseLeft = Mathf.Max(0f, pulseLeft - Time.unscaledDeltaTime);
                var t = 1f - pulseLeft / pulseSeconds;
                transform.localScale = baseScale * Mathf.Lerp(1f, pulseScale, Mathf.Sin(t * Mathf.PI));
            }
            if (hero == null || hero.Combatant == null || hero.Combatant.IsDead) return;
            if (hero.Checkpoint == transform) return;
            var d = hero.transform.position - transform.position;
            d.y = 0f;
            if (d.sqrMagnitude <= radius * radius) Reach();
        }

        void Reach()
        {
            hero.SetCheckpoint(transform);
            hero.Logic?.RefillPotions(); // a regra de encher é do core (IPotionBelt.Refill), a mesma do Revive
            pulseLeft = pulseSeconds;
            combatHost = CombatSystemHost.Resolve(combatHost, this);
            var evt = new CheckpointReachedEvent { CheckpointId = checkpointId, Position = transform.position };
            combatHost?.Events?.Publish(in evt);
        }
    }
}
