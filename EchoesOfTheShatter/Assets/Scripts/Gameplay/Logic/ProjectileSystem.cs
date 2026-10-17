using System.Collections.Generic;

namespace Echoes.Gameplay
{
    /// <summary>
    /// Projéteis em passo fixo, em pool (limite de 300 ativos; docs/04_arquitetura.md, seção 10.4).
    /// Cada projétil acerta o primeiro alvo hostil que tocar e some (1 acerto por projétil).
    /// </summary>
    public sealed class ProjectileSystem
    {
        public const int MaxActive = 300;

        readonly List<ProjectileState> active = new List<ProjectileState>(32);
        readonly Stack<ProjectileState> pool = new Stack<ProjectileState>(32);
        int nextId = 1;

        public IReadOnlyList<ProjectileState> Active => active;

        /// <summary>
        /// Meia largura do corredor do projétil: o raio do CSV, exceto em quem explode (ali o raio é o da explosão, e o corpo do projétil é um ponto).
        /// </summary>
        public static float BodyRadiusMeters(Echoes.Interop.SkillInfo skill)
        {
            return skill.Behavior.Explodes ? 0f : WorldUnits.ToMeters(skill.RadiusUu);
        }

        public ProjectileState Spawn(CombatSystem combat, Combatant owner, Echoes.Interop.SkillInfo skill, PlanarVector origin,
            PlanarVector direction, float speed, float rangeMeters, float radiusMeters, double hitMultiplier = 1.0)
        {
            if (active.Count >= MaxActive || speed <= 0f || rangeMeters <= 0f) return null;
            var p = pool.Count > 0 ? pool.Pop() : new ProjectileState();
            p.Id = nextId++;
            p.Owner = owner;
            p.Skill = skill;
            p.Position = origin;
            p.Direction = direction.NormalizedOr(PlanarVector.Forward);
            p.SpeedMetersPerSecond = speed;
            p.RemainingMeters = rangeMeters;
            p.RadiusMeters = radiusMeters;
            p.HitMultiplier = hitMultiplier;
            p.HitTargets.Clear();
            // Perfuração (SkillInfo.Pierce): N alvos além do primeiro; 99 atravessa todos. Explosão (Behavior.Explodes): dano em área onde o projétil acaba.
            // TODO(backend): o raio da explosão virá de SkillInfo.ExplosionRadiusUu; até lá é o radius do CSV, que nas habilidades que explodem já é o da explosão.
            p.MaxHits = skill.Pierce <= 0 ? 1 : skill.Pierce >= Echoes.Interop.SkillInfo.PierceAll ? int.MaxValue : skill.Pierce + 1;
            p.ExplosionRadiusMeters = skill.Behavior.Explodes ? WorldUnits.ToMeters(skill.RadiusUu) : 0f;
            p.Active = true;
            active.Add(p);
            var evt = new ProjectileEvent { ProjectileId = p.Id, Spawned = true, Owner = owner, Position = origin, Direction = p.Direction };
            combat.Events.Publish(in evt);
            return p;
        }

        readonly List<Candidate> candidates = new List<Candidate>(8);

        struct Candidate
        {
            public Combatant Target;
            public float T;
        }

        public void Step(CombatSystem combat, double dt)
        {
            for (var i = active.Count - 1; i >= 0; i--)
            {
                var p = active[i];
                var travel = (float)(p.SpeedMetersPerSecond * dt);
                if (travel > p.RemainingMeters) travel = p.RemainingMeters;
                var start = p.Position;
                var end = start + p.Direction * travel;
                p.Position = end;
                p.RemainingMeters -= travel;

                // Alvos tocados neste passo, do mais perto ao mais longe ao longo do caminho (a perfuração acerta na ordem do voo).
                candidates.Clear();
                var targets = combat.Combatants;
                for (var t = 0; t < targets.Count; t++)
                {
                    var target = targets[t];
                    if (target.IsDead || !CombatSystem.AreHostile(p.Owner, target) || p.HitTargets.Contains(target.Id)) continue;
                    if (!ShapeQuery.InCorridor(start, end, p.RadiusMeters, target.Position, target.RadiusMeters)) continue;
                    var c = new Candidate { Target = target, T = ProjectOnSegment(start, end, target.Position) };
                    var at = candidates.Count;
                    while (at > 0 && candidates[at - 1].T > c.T) at--;
                    candidates.Insert(at, c);
                }

                var ended = false;
                for (var c = 0; c < candidates.Count && !ended; c++)
                {
                    var target = candidates[c].Target;
                    if (target.IsDead) continue;
                    var contact = start + (end - start) * candidates[c].T;
                    if (p.ExplosionRadiusMeters > 0f)
                    {
                        p.Position = contact;
                        Explode(combat, p, contact);
                        ended = true;
                        break;
                    }
                    p.HitTargets.Add(target.Id);
                    combat.ApplySkillHit(p.Owner, target, p.Skill, start, p.HitMultiplier);
                    if (p.HitTargets.Count >= p.MaxHits)
                    {
                        p.Position = contact;
                        ended = true;
                    }
                }

                if (ended || p.RemainingMeters <= 0f) End(combat, i);
            }
        }

        // Explosão: um acerto por alvo hostil dentro do raio, centrada no ponto do impacto (RF-16); o alvo atingido de frente também está no círculo.
        void Explode(CombatSystem combat, ProjectileState p, PlanarVector center)
        {
            var targets = combat.Combatants;
            for (var t = 0; t < targets.Count; t++)
            {
                var target = targets[t];
                if (target.IsDead || !CombatSystem.AreHostile(p.Owner, target) || p.HitTargets.Contains(target.Id)) continue;
                if (!ShapeQuery.InCircle(center, p.ExplosionRadiusMeters, target.Position, target.RadiusMeters)) continue;
                p.HitTargets.Add(target.Id);
                combat.ApplySkillHit(p.Owner, target, p.Skill, center, p.HitMultiplier);
            }
        }

        static float ProjectOnSegment(PlanarVector a, PlanarVector b, PlanarVector point)
        {
            var ab = b - a;
            var lengthSq = ab.SqrMagnitude;
            if (lengthSq < 1e-8f) return 0f;
            var t = PlanarVector.Dot(point - a, ab) / lengthSq;
            return t < 0f ? 0f : t > 1f ? 1f : t;
        }

        public void Clear(CombatSystem combat)
        {
            for (var i = active.Count - 1; i >= 0; i--) End(combat, i);
        }

        void End(CombatSystem combat, int index)
        {
            var p = active[index];
            active.RemoveAt(index);
            p.Active = false;
            var evt = new ProjectileEvent { ProjectileId = p.Id, Spawned = false, Owner = p.Owner, Position = p.Position, Direction = p.Direction, ExplosionRadiusMeters = p.HitTargets.Count > 0 ? p.ExplosionRadiusMeters : 0f };
            p.Owner = null;
            p.Skill = null;
            pool.Push(p);
            combat.Events.Publish(in evt);
        }
    }
}
