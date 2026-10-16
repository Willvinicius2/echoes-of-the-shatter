using UnityEngine;

namespace Echoes.Gameplay
{
    /// <summary>
    /// Encontros da Cripta (decisão do dono): ao voltar ao checkpoint (morte ou saída) os inimigos já mortos REAPARECEM, no ponto de
    /// nascimento e com vida cheia. O chefe é do <see cref="ArenaController"/> (reinicia a luta; vencido, fica vencido).
    /// </summary>
    public sealed class EncounterDirector : MonoBehaviour
    {
        [SerializeField] HeroController hero;
        [SerializeField] ArenaController arena;
        [SerializeField] EnemyController[] enemies;

        public int EnemyCount => enemies != null ? enemies.Length : 0;

        void Start()
        {
            if (hero != null) hero.Respawned += ResetEncounters;
        }

        void OnDestroy()
        {
            if (hero != null) hero.Respawned -= ResetEncounters;
        }

        /// <summary>Reaparece todo mundo (menos o chefe, que a arena cuida).</summary>
        public void ResetEncounters()
        {
            if (enemies == null) return;
            for (var i = 0; i < enemies.Length; i++)
            {
                var enemy = enemies[i];
                if (enemy == null || (arena != null && ReferenceEquals(enemy, arena.Boss))) continue;
                enemy.ResetToSpawn(false);
            }
        }
    }
}
