using UnityEngine;

namespace Echoes.Gameplay
{
    /// <summary>
    /// Checkpoint da Cripta: o herói que passa dentro do raio fixa este ponto como o de retorno (RF-18). Enche poções ao voltar
    /// (o core faz no Revive) e os inimigos mortos reaparecem (<see cref="EncounterDirector"/>).
    /// </summary>
    public sealed class CheckpointZone : MonoBehaviour
    {
        [SerializeField] HeroController hero;
        [Tooltip("Raio do ponto de ativação, em metros (técnico).")]
        [SerializeField, Min(0.5f)] float radius = 3f;
        [SerializeField] string checkpointId;

        public string CheckpointId => checkpointId;

        void Update()
        {
            if (hero == null || hero.Combatant == null || hero.Combatant.IsDead) return;
            if (hero.Checkpoint == transform) return;
            var d = hero.transform.position - transform.position;
            d.y = 0f;
            if (d.sqrMagnitude <= radius * radius) hero.SetCheckpoint(transform);
        }
    }
}
