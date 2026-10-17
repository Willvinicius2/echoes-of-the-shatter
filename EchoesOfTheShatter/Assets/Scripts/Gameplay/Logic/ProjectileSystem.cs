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
            p.Active = true;
            active.Add(p);
            var evt = new ProjectileEvent { ProjectileId = p.Id, Spawned = true, Owner = owner, Position = origin, Direction = p.Direction };
            combat.Events.Publish(in evt);
            return p;
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

                var hit = false;
                var targets = combat.Combatants;
                for (var t = 0; t < targets.Count; t++)
                {
                    var target = targets[t];
                    if (target.IsDead || !CombatSystem.AreHostile(p.Owner, target)) continue;
                    if (!ShapeQuery.InCorridor(start, end, p.RadiusMeters, target.Position, target.RadiusMeters)) continue;
                    combat.ApplySkillHit(p.Owner, target, p.Skill, start, p.HitMultiplier);
                    hit = true;
                    break;
                }

                if (hit || p.RemainingMeters <= 0f) End(combat, i);
            }
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
            var evt = new ProjectileEvent { ProjectileId = p.Id, Spawned = false, Owner = p.Owner, Position = p.Position, Direction = p.Direction };
            p.Owner = null;
            p.Skill = null;
            pool.Push(p);
            combat.Events.Publish(in evt);
        }
    }
}
