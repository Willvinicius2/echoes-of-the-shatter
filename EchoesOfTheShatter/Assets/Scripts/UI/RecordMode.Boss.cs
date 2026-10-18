using System;
using System.Collections.Generic;
using System.Text;
using Echoes.Gameplay;
using Echoes.Interop;
using UnityEngine;

namespace Echoes.UI
{
    /// <summary>
    /// Demo do Guardião (rev6, <c>-scenario boss</c>): o herói contorna o escudo frontal (120°) e ataca de lado e por trás; três golpes fortes seguidos
    /// dão a Guarda Quebrada (stagger de 1,5 s e escudo caído por 5 s); depois um dano de gravação (<see cref="EnemyCombatLogic.DevDamageBoss"/>,
    /// só no modo de gravação) leva a vida do chefe perto de 50% para a fase 2 (rugido e invocação sem a luta inteira); no fim o herói se põe atrás
    /// de um pilar para a Investida do Escudo bater nele. Os eventos do chefe vão para boss_events.txt.
    /// </summary>
    public sealed partial class RecordMode
    {
        bool bossPhase2;
        bool bossGuardBroke;
        int bossStaggers;
        int bossSummons;
        readonly StringBuilder bossLog = new StringBuilder();
        Func<Vector3> walkToPoint;

        void OnBossEvent(in BossStateEvent evt)
        {
            if (traceEnemy == null || evt.Owner != traceEnemy.Combatant) return;
            bossLog.AppendLine($"{frame}\t{frame / (float)Fps:F2}s\t{evt.Kind}\tfase {evt.Phase}\t{evt.Seconds:F2}s\t{evt.EnemyId}\t{evt.Count}");
            if (evt.Kind == BossEventKind.PhaseStart && evt.Phase >= 2) bossPhase2 = true;
            if (evt.Kind == BossEventKind.StaggerStart) bossStaggers++;
            if (evt.Kind == BossEventKind.ShieldDown) bossGuardBroke = true;
            if (evt.Kind == BossEventKind.SummonSpawn) bossSummons += Mathf.Max(1, evt.Count);
        }

        // Anda ate o ponto (recalculado a cada quadro) ou ate o tempo acabar; devolve quando chega.
        IEnumerator<Func<bool>> WalkTo(Func<Vector3> point, HeroController hero, float tolerance, float timeoutSeconds)
        {
            walkToPoint = point;
            var deadline = frame + Mathf.RoundToInt(timeoutSeconds * Fps);
            yield return Until(() => frame >= deadline || Vector3.Distance(Flat(hero.transform.position), Flat(point())) <= tolerance);
            walkToPoint = null;
            yield return Frames(3);
        }

        static Vector3 Flat(Vector3 v) => new Vector3(v.x, 0f, v.z);

        // Angulo (graus) entre a frente do chefe e a direcao chefe -> heroi: > 60 = fora do arco do escudo (120 graus).
        static float AngleFromBossFront(EnemyController boss, Vector3 heroPosition)
        {
            var forward = Flat(boss.transform.forward).normalized;
            var toHero = Flat(heroPosition - boss.transform.position).normalized;
            return Vector3.Angle(forward, toHero);
        }

        // Ponto ao lado/atras do chefe, do lado em que o herói ja esta: a 'angle' graus da frente, a 'distance' m do centro.
        Vector3 FlankPoint(EnemyController boss, HeroController hero, float angle, float distance)
        {
            var forward = Flat(boss.transform.forward).normalized;
            var right = Flat(boss.transform.right).normalized;
            var side = Vector3.Dot(Flat(hero.transform.position - boss.transform.position), right) >= 0f ? 1f : -1f;
            var direction = Quaternion.AngleAxis(side * angle, Vector3.up) * forward;
            return boss.transform.position + direction * distance;
        }

        // Um colider fino e alto perto do chefe (pilar da arena), ou null.
        static Collider FindPillar(EnemyController boss)
        {
            Collider best = null;
            var bestDistance = float.MaxValue;
            foreach (var collider in Physics.OverlapSphere(boss.transform.position, 16f, ~0, QueryTriggerInteraction.Ignore))
            {
                if (collider.GetComponentInParent<CharacterController>() != null || collider.transform.IsChildOf(boss.transform)) continue;
                var size = collider.bounds.size;
                if (size.y < 1.8f || Mathf.Max(size.x, size.z) > 4.5f) continue;
                var named = collider.name.IndexOf("pil", StringComparison.OrdinalIgnoreCase) >= 0 || collider.transform.root.name.IndexOf("pil", StringComparison.OrdinalIgnoreCase) >= 0;
                var distance = Vector3.Distance(collider.bounds.center, boss.transform.position) - (named ? 6f : 0f);
                if (distance < 3f) continue;
                if (distance < bestDistance)
                {
                    best = collider;
                    bestDistance = distance;
                }
            }
            return best;
        }

        IEnumerator<Func<bool>> BossSteps(HeroController hero, EnemyController boss, float maxSeconds)
        {
            var logic = boss.Logic;
            var endFrame = Mathf.RoundToInt(maxSeconds * Fps) - 2 * Fps;

            // 1) o heroi espera: o Guardiao vem e telegrafa (martelo e escudada)
            yield return Sec(5f);

            // 2) fase 1: contorna o escudo. Tres golpes fortes seguidos (Guarda Quebrada) e depois combos.
            var phase1End = frame + 34 * Fps;
            var heavies = 0;
            var comboRounds = 0;
            while (frame < phase1End && frame < endFrame && !bossPhase2)
            {
                // O chefe gira 60 graus/s para o heroi: o forte (carga curta + preparacao) leva ~0,6 s, entao o heroi chega por tras (150 graus) para
                // ainda estar fora do arco do escudo (60 graus de cada lado) quando o golpe cair.
                var to = WalkTo(() => FlankPoint(boss, hero, 150f, 2.2f), hero, 0.5f, 4f);
                while (to.MoveNext()) yield return to.Current;
                if (AngleFromBossFront(boss, hero.transform.position) < 100f && !bossGuardBroke) continue; // ainda perto do arco do escudo: contorna de novo
                if (!bossGuardBroke && heavies < 9)
                {
                    var heavy = Charge(hero, 0.45f);
                    while (heavy.MoveNext()) yield return heavy.Current;
                    heavies++;
                }
                else
                {
                    for (var i = 0; i < 3; i++)
                    {
                        var strike = Strike(hero);
                        while (strike.MoveNext()) yield return strike.Current;
                    }
                    comboRounds++;
                    if (bossGuardBroke && comboRounds >= 4) break;
                }
            }

            // 3) dano de gravacao por tras: leva o chefe perto de 50% da vida (fase 2 sem a luta inteira)
            var guard = 0;
            while (!bossPhase2 && guard++ < 40 && frame < endFrame)
            {
                var info = logic.BossInfo;
                if (info.MaxLife <= 0.0 || info.Life / info.MaxLife <= 0.53) break;
                var behind = boss.transform.position - Flat(boss.transform.forward).normalized * 3f;
                logic.DevDamageBoss(Math.Max(1.0, info.MaxLife * 0.04), new PlanarVector(behind.x, behind.z));
                yield return Frames(2);
            }
            // um golpe de verdade cruza o limiar: rugido (invulneravel) e invocacao
            var cross = frame + 12 * Fps;
            while (!bossPhase2 && frame < cross && frame < endFrame)
            {
                var to = WalkTo(() => FlankPoint(boss, hero, 110f, 2.2f), hero, 0.6f, 3f);
                while (to.MoveNext()) yield return to.Current;
                var strike = Strike(hero);
                while (strike.MoveNext()) yield return strike.Current;
            }
            var roarEnd = frame + 5 * Fps;
            yield return Until(() => frame >= roarEnd);

            // 4) fase 2: o heroi se poe atras de um pilar, no lado oposto ao chefe, para a Investida do Escudo bater nele
            var pillar = FindPillar(boss);
            var staggersBefore = bossStaggers;
            var wait = frame + 28 * Fps;
            if (pillar != null)
            {
                var pillarCenter = pillar.bounds.center;
                var radius = Mathf.Max(pillar.bounds.extents.x, pillar.bounds.extents.z);
                Func<Vector3> behindPillar = () =>
                {
                    var away = Flat(pillarCenter - boss.transform.position).normalized;
                    return Flat(pillarCenter) + away * (radius + 2.2f);
                };
                bossLog.AppendLine($"{frame}\tpilar\t{pillar.name}\t{pillarCenter}");
                while (frame < wait && frame < endFrame && bossStaggers == staggersBefore)
                {
                    var to = WalkTo(behindPillar, hero, 0.5f, 3f);
                    while (to.MoveNext()) yield return to.Current;
                    yield return Sec(0.6f);
                }
            }
            else bossLog.AppendLine($"{frame}\tsem pilar encontrado");

            // 5) o chefe (de escudo caido ou em stagger) apanha por mais alguns segundos
            var finish = Mathf.Min(endFrame, frame + 6 * Fps);
            while (frame < finish)
            {
                var to = WalkTo(() => FlankPoint(boss, hero, 100f, 2.0f), hero, 0.6f, 3f);
                while (to.MoveNext()) yield return to.Current;
                var strike = Strike(hero);
                while (strike.MoveNext()) yield return strike.Current;
            }
            yield return Sec(1.5f);
        }
    }
}
