using UnityEngine;

namespace Echoes.Gameplay
{
    /// <summary>
    /// Luta do Guardião (docs/14 seção 6.3; decisão do dono): o herói entrando no gatilho fecha a porta da arena atrás dele e acorda o
    /// chefe; a porta só reabre quando a luta acaba (vitória ou morte do herói). Morte reinicia a luta na hora: o herói volta ao início
    /// da arena e o chefe volta parado. A vitória revela o Marco de Retorno e o portal de saída.
    /// </summary>
    public sealed class ArenaController : MonoBehaviour
    {
        [SerializeField] CombatSystemHost combatHost;
        [SerializeField] HeroController hero;
        [SerializeField] EnemyController boss;
        [SerializeField] GateBarrier gate;
        [Tooltip("Ponto de reinício da luta (spawn.crypt.arena); também vira o checkpoint durante a luta.")]
        [SerializeField] Transform arenaSpawn;
        [Tooltip("Retângulo do gatilho no mundo: x = x0, y = z0, largura = x1 - x0, altura = z1 - z0.")]
        [SerializeField] Rect trigger;
        [Tooltip("Aparecem ao vencer: Marco de Retorno e portal de saída.")]
        [SerializeField] GameObject[] revealOnVictory;

        public ArenaPhase Phase { get; private set; }
        public Rect Trigger => trigger;
        public EnemyController Boss => boss;

        void Start()
        {
            SetVictoryVisible(false);
            if (hero != null) hero.Respawned += OnHeroRespawned;
        }

        void OnDestroy()
        {
            if (hero != null) hero.Respawned -= OnHeroRespawned;
        }

        void Update()
        {
            if (hero == null || boss == null || hero.Combatant == null) return;
            switch (Phase)
            {
                case ArenaPhase.Waiting:
                    if (!hero.Combatant.IsDead && trigger.Contains(new Vector2(hero.transform.position.x, hero.transform.position.z))) StartFight();
                    break;
                case ArenaPhase.Fighting:
                    if (boss.Combatant != null && boss.Combatant.IsDead) EndFight(ArenaPhase.Won);
                    break;
            }
        }

        void StartFight()
        {
            Phase = ArenaPhase.Fighting;
            gate?.Close();
            hero.SetCheckpoint(arenaSpawn);
            boss.Activate();
            Publish();
        }

        void EndFight(ArenaPhase phase)
        {
            Phase = phase;
            gate?.Open();
            if (phase == ArenaPhase.Won) SetVictoryVisible(true);
            Publish();
        }

        // Morte (ou saída pelo portal) durante a luta: a luta reinicia, a porta reabre e o chefe volta parado até o gatilho de novo.
        void OnHeroRespawned()
        {
            if (Phase != ArenaPhase.Fighting) return;
            gate?.Open();
            boss.ResetToSpawn(true);
            Phase = ArenaPhase.Waiting;
            Publish();
        }

        void SetVictoryVisible(bool visible)
        {
            if (revealOnVictory == null) return;
            for (var i = 0; i < revealOnVictory.Length; i++)
            {
                if (revealOnVictory[i] != null) revealOnVictory[i].SetActive(visible);
            }
        }

        void Publish()
        {
            var evt = new ArenaStateEvent { Phase = Phase };
            combatHost?.Events?.Publish(in evt);
        }
    }
}
