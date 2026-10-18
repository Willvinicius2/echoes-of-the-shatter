using System;
using System.Collections.Generic;
using Echoes.Core;
using Echoes.Interop;
using Echoes.Interop.Native;
using UnityEngine;

namespace Echoes.Gameplay
{
    /// <summary>
    /// Encontros da Cripta. (1) Sorteio pelo core (docs/09 seção 14, shatter_encounter_roll): ao entrar na Cripta começa uma visita (o core
    /// incrementa o contador e dá a semente) e cada encontro vira n inimigos entre o mínimo e o máximo do CSV, com elites sorteados por espaço
    /// (modificador do core). A cena traz o máximo; quem não foi sorteado é desligado. A formação é a mesma depois de um checkpoint (mesma semente).
    /// (2) Ao voltar ao checkpoint (morte ou saída) os inimigos mortos REAPARECEM no ponto de nascimento, com vida cheia (decisão do dono).
    /// O chefe é do <see cref="ArenaController"/>. (3) Limpar um encontro (a primeira vez na visita) publica <see cref="EncounterClearedEvent"/>.
    /// Sem save (cena aberta direto no editor) fica o máximo do layout, como antes.
    /// </summary>
    [DefaultExecutionOrder(-960)]
    public sealed class EncounterDirector : MonoBehaviour
    {
        /// <summary>Um inimigo da cena e o espaço do encontro que ele ocupa: o grupo é a n-ésima ocorrência desse inimigo no encontro (ordem do CSV).</summary>
        [Serializable]
        public struct Slot
        {
            public EnemyController enemy;
            public string encounterId;
            public int groupOrdinal;
            public int slot;
        }

        [SerializeField] CombatSystemHost combatHost;
        [SerializeField] HeroController hero;
        [SerializeField] ArenaController arena;
        [SerializeField] EnemyController[] enemies;
        [Tooltip("Espaços do layout por encontro (preenchido pelo CriptaBuilder); vazio = sem sorteio do core.")]
        [SerializeField] Slot[] slots = Array.Empty<Slot>();

        readonly Dictionary<string, RolledEncounterInfo> rolled = new Dictionary<string, RolledEncounterInfo>();
        readonly HashSet<string> cleared = new HashSet<string>();
        bool subscribed;

        public int EnemyCount => enemies != null ? enemies.Length : 0;

        /// <summary>Semente da visita (0 se o core não sorteou: sem save).</summary>
        public ulong VisitSeed { get; private set; }

        /// <summary>O que o core sorteou para o encontro (null se não há sorteio).</summary>
        public RolledEncounterInfo RolledFor(string encounterId) => rolled.TryGetValue(encounterId, out var info) ? info : null;

        public bool IsCleared(string encounterId) => cleared.Contains(encounterId);

        void Awake()
        {
            var root = FindAnyObjectByType<GameRoot>();
            var rules = GameSession.NativeRules(root);
            if (rules == null || GameSession.Save == null || !GameSession.Save.HasSave || slots == null || slots.Length == 0) return;
            ApplyRolls(rules, GameSession.Save.Current);
        }

        void ApplyRolls(NativeRulesCore rules, SaveGame save)
        {
            if (!save.BeginAreaVisit(rules, ExpeditionConfig.CryptMap, out var seed))
            {
                Debug.LogWarning("[Encounters] O core nao comecou a visita; fica o maximo do layout.");
                return;
            }
            VisitSeed = seed;
            foreach (var entry in slots)
            {
                if (entry.enemy == null) continue;
                if (!rolled.TryGetValue(entry.encounterId, out var info))
                {
                    info = SaveGame.RollEncounter(rules, entry.encounterId, seed);
                    rolled[entry.encounterId] = info;
                }
                if (info.IsBoss) continue;
                var group = GroupOf(info, entry.enemy.EnemyId, entry.groupOrdinal);
                if (group == null || entry.slot >= group.Count)
                {
                    entry.enemy.Exclude(); // o core sorteou menos inimigos que o maximo do layout
                    continue;
                }
                var rolledSlot = group.Slots[entry.slot];
                entry.enemy.ApplyRoll(rolledSlot.Elite, rolledSlot.ModifierId);
            }
        }

        static RolledGroupInfo GroupOf(RolledEncounterInfo info, string enemyId, int ordinal)
        {
            var seen = 0;
            foreach (var group in info.Groups)
            {
                if (group.EnemyId != enemyId) continue;
                if (seen == ordinal) return group;
                seen++;
            }
            return null;
        }

        void Start()
        {
            if (hero != null) hero.Respawned += ResetEncounters;
            combatHost = CombatSystemHost.Resolve(combatHost, this);
            var events = combatHost != null ? combatHost.Events : null;
            if (events == null) return;
            events.Subscribe<CombatantDiedEvent>(OnDied);
            subscribed = true;
        }

        void OnDestroy()
        {
            if (hero != null) hero.Respawned -= ResetEncounters;
            var events = combatHost != null ? combatHost.Events : null;
            if (subscribed && events != null) events.Unsubscribe<CombatantDiedEvent>(OnDied);
        }

        // Limpou o encontro: todos os inimigos sorteados dele estao mortos. So a primeira vez na visita (sem farm de reaparecer no checkpoint).
        void OnDied(in CombatantDiedEvent evt)
        {
            if (evt.Target == null || evt.Target.Team != CombatTeam.Enemy || slots == null) return;
            string encounterId = null;
            foreach (var entry in slots)
            {
                if (entry.enemy != null && ReferenceEquals(entry.enemy.Combatant, evt.Target)) { encounterId = entry.encounterId; break; }
            }
            if (encounterId == null || cleared.Contains(encounterId)) return;
            if (rolled.TryGetValue(encounterId, out var info) && info.IsBoss) return;
            foreach (var entry in slots)
            {
                if (entry.encounterId != encounterId || entry.enemy == null || entry.enemy.Excluded) continue;
                var combatant = entry.enemy.Combatant;
                if (combatant == null || !combatant.IsDead) return; // ainda tem alguem vivo (ou que nem acordou)
            }
            cleared.Add(encounterId);
            var evtOut = new EncounterClearedEvent { EncounterId = encounterId, Position = new Vector3(evt.Target.Position.X, 0f, evt.Target.Position.Z) };
            combatHost?.Events?.Publish(in evtOut);
        }

        /// <summary>Reaparece todo mundo (menos o chefe, que a arena cuida, e quem o sorteio deixou de fora).</summary>
        public void ResetEncounters()
        {
            if (enemies == null) return;
            for (var i = 0; i < enemies.Length; i++)
            {
                var enemy = enemies[i];
                if (enemy == null || enemy.Excluded || (arena != null && ReferenceEquals(enemy, arena.Boss))) continue;
                enemy.ResetToSpawn(false);
            }
        }
    }
}
