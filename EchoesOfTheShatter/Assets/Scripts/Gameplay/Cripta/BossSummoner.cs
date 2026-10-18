using System.Collections.Generic;
using Echoes.Interop;
using UnityEngine;

namespace Echoes.Gameplay
{
    /// <summary>
    /// Fase 2 do Guardião (docs/14 6.3, docs/13 item 6): quando o core sinaliza a invocação (<see cref="BossEventKind.SummonSpawn"/>, uma vez por luta)
    /// nascem as Sentinelas nas <c>summonMarks</c> do layout. Quantidade e inimigo vêm do evento (boss_phases.csv), nunca do código. As invocadas
    /// somem quando a luta acaba (vitória) ou reinicia (morte do herói). O molde (<see cref="template"/>) fica desativado na cena.
    /// </summary>
    public sealed class BossSummoner : MonoBehaviour
    {
        [SerializeField] CombatSystemHost combatHost;
        [SerializeField] ArenaController arena;
        [Tooltip("Sentinela desativada usada como molde (mesmo prefab dos encontros).")]
        [SerializeField] EnemyController template;
        [Tooltip("Pontos de invocação do layout (docs/14, summonMarks), em coordenadas de mundo.")]
        [SerializeField] Vector3[] marks = System.Array.Empty<Vector3>();
        [Tooltip("Afastamento (m) entre invocadas que dividem o mesmo ponto (técnico).")]
        [SerializeField, Min(0f)] float stackSpacing = 1.5f;

        readonly List<EnemyController> spawned = new List<EnemyController>();
        bool subscribed;

        public IReadOnlyList<EnemyController> Spawned => spawned;

        /// <summary>Posição da n-ésima invocada: pontos em rodízio; quem repete um ponto sai ao lado (regra pura, testável).</summary>
        public static Vector3 PositionFor(IReadOnlyList<Vector3> points, int index, float spacing)
        {
            if (points == null || points.Count == 0) return Vector3.zero;
            var round = index / points.Count;
            return points[index % points.Count] + Vector3.right * (round * spacing);
        }

        void Start()
        {
            combatHost = CombatSystemHost.Resolve(combatHost, this);
            if (arena == null) arena = FindAnyObjectByType<ArenaController>();
            var events = combatHost != null ? combatHost.Events : null;
            if (events == null) return;
            events.Subscribe<BossStateEvent>(OnBossState);
            events.Subscribe<ArenaStateEvent>(OnArena);
            subscribed = true;
        }

        void OnDestroy()
        {
            var events = combatHost != null ? combatHost.Events : null;
            if (!subscribed || events == null) return;
            events.Unsubscribe<BossStateEvent>(OnBossState);
            events.Unsubscribe<ArenaStateEvent>(OnArena);
        }

        void OnBossState(in BossStateEvent evt)
        {
            if (evt.Kind != BossEventKind.SummonSpawn) return;
            var boss = arena != null && arena.Boss != null ? arena.Boss.Combatant : null;
            if (boss != null && !ReferenceEquals(boss, evt.Owner)) return;
            Spawn(evt.Count, evt.EnemyId);
        }

        void OnArena(in ArenaStateEvent evt)
        {
            if (evt.Phase != ArenaPhase.Fighting) Clear();
        }

        /// <summary>Cria <paramref name="count"/> invocadas (o molde precisa ser do mesmo inimigo pedido).</summary>
        public int Spawn(int count, string enemyId)
        {
            if (template == null || marks.Length == 0 || count <= 0) return 0;
            if (!string.IsNullOrEmpty(enemyId) && template.EnemyId != enemyId)
            {
                Debug.LogWarning($"[Summon] O molde é '{template.EnemyId}', o core pediu '{enemyId}': invocação ignorada.", this);
                return 0;
            }
            Clear();
            var toward = arena != null && arena.Boss != null ? arena.Boss.transform.position : transform.position;
            for (var i = 0; i < count; i++)
            {
                var position = PositionFor(marks, i, stackSpacing);
                var look = toward - position;
                look.y = 0f;
                var rotation = look.sqrMagnitude > 0.01f ? Quaternion.LookRotation(look) : Quaternion.identity;
                var copy = Instantiate(template, position, rotation, transform);
                copy.name = template.name + "_summon" + (i + 1);
                copy.gameObject.SetActive(true);
                spawned.Add(copy);
            }
            return spawned.Count;
        }

        /// <summary>Remove as invocadas (fim ou reinício da luta).</summary>
        public void Clear()
        {
            for (var i = 0; i < spawned.Count; i++)
            {
                if (spawned[i] != null) Destroy(spawned[i].gameObject);
            }
            spawned.Clear();
        }
    }
}
