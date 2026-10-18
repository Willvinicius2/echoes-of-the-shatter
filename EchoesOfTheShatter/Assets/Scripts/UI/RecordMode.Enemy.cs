using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Text;
using Echoes.Gameplay;
using Echoes.Presentation;
using UnityEngine;

namespace Echoes.UI
{
    /// <summary>
    /// Roteiros de gravação dos inimigos (rev5): <c>-scenario enemy -enemy ID</c> (câmera no meio entre o herói e o inimigo: ele vem, telegrafa e
    /// ataca; depois o herói luta até a morte) e <c>-scenario mixed</c> (o herói limpa o grupo de inimigos mais cheio, câmera do jogo).
    /// Mesmos argumentos de câmera do RecordMode (-camdist, -campitch). Escreve trace_enemy.csv por quadro (posição, velocidade, giro,
    /// estado da IA, fase do golpe e o clipe de cada camada do Animator).
    /// </summary>
    public sealed partial class RecordMode
    {
        static EnemyController scenarioTarget;
        EnemyController traceEnemy;
        int enemyImpacts;
        string enemyPhase = "";
        readonly StringBuilder enemyTrace = new StringBuilder("frame,t,x,z,speed_mps,yaw_deg,turn_dps,state,phase,dead,fleeing,wantsMove,distHero,L0,L0w,L1,L1w,L2,L2w,modelOffset,agent,agentVel,path,remaining,dormant,agentSpeed,agentAccel,chaseSpeed,stopDist\n");
        Vector3 enemyPrev;
        float enemyPrevYaw;
        bool enemyTraceFirst = true;

        static EnemyController FindEnemy(string id, Vector3 from)
        {
            EnemyController best = null;
            var bestDistance = float.MaxValue;
            foreach (var enemy in FindObjectsByType<EnemyController>(FindObjectsSortMode.None))
            {
                if (enemy.Combatant == null || enemy.EnemyId != id) continue;
                var d = (enemy.transform.position - from).sqrMagnitude;
                if (d < bestDistance)
                {
                    best = enemy;
                    bestDistance = d;
                }
            }
            return best;
        }

        // O inimigo com mais vizinhos num raio de 12 m (o maior grupo da Cripta) para o combate misto.
        static EnemyController BusiestEnemy()
        {
            EnemyController best = null;
            var bestCount = -1;
            var all = FindObjectsByType<EnemyController>(FindObjectsSortMode.None);
            foreach (var enemy in all)
            {
                if (enemy.Combatant == null || enemy.Combatant.IsBoss) continue;
                var count = 0;
                foreach (var other in all)
                {
                    if (other == enemy || other.Combatant == null || other.Combatant.IsBoss) continue;
                    if ((other.transform.position - enemy.transform.position).sqrMagnitude < 12f * 12f) count++;
                }
                if (count > bestCount)
                {
                    best = enemy;
                    bestCount = count;
                }
            }
            return best;
        }

        void OnEnemyPhase(in SkillPhaseEvent evt)
        {
            if (traceEnemy == null || evt.Owner != traceEnemy.Combatant) return;
            enemyPhase = evt.Phase.ToString();
            if (evt.Phase == ActionPhase.Impact) enemyImpacts++;
        }

        void EnemyTraceRow(int index)
        {
            var enemy = traceEnemy;
            if (enemy == null || enemy.Logic == null) return;
            var dt = 1f / Fps;
            var pos = enemy.transform.position;
            var yaw = enemy.transform.eulerAngles.y;
            var speed = enemyTraceFirst ? 0f : new Vector2(pos.x - enemyPrev.x, pos.z - enemyPrev.z).magnitude / dt;
            var turn = enemyTraceFirst ? 0f : Mathf.DeltaAngle(enemyPrevYaw, yaw) / dt;
            enemyPrev = pos;
            enemyPrevYaw = yaw;
            enemyTraceFirst = false;
            var animator = enemy.GetComponentInChildren<Animator>();
            string Layer(int layer, out float weight)
            {
                weight = 0f;
                if (animator == null || layer >= animator.layerCount) return "";
                var infos = animator.GetCurrentAnimatorClipInfo(layer);
                if (infos.Length == 0) return "-";
                var best = infos[0];
                foreach (var info in infos) if (info.weight > best.weight) best = info;
                weight = best.weight;
                return best.clip.name;
            }
            var l0 = Layer(0, out var w0);
            var l1 = Layer(1, out var w1);
            var l2 = Layer(2, out var w2);
            var inv = System.Globalization.CultureInfo.InvariantCulture;
            var agentInfo = enemy.GetComponent<UnityEngine.AI.NavMeshAgent>();
            var hero = traceHero;
            var distHero = hero != null ? Vector3.Distance(hero.transform.position, pos) : 0f;
            var offset = animator != null && animator.transform != enemy.transform ? animator.transform.localPosition.magnitude : 0f;
            enemyTrace.Append(index).Append(',').Append((index * dt).ToString("F3", inv)).Append(',').Append(pos.x.ToString("F3", inv)).Append(',').Append(pos.z.ToString("F3", inv))
                .Append(',').Append(speed.ToString("F2", inv)).Append(',').Append(yaw.ToString("F1", inv)).Append(',').Append(turn.ToString("F0", inv))
                .Append(',').Append(enemy.Logic.Brain.State).Append(',').Append(enemyPhase).Append(',').Append(enemy.Combatant.IsDead ? 1 : 0).Append(',').Append(enemy.Logic.IsFleeing ? 1 : 0)
                .Append(',').Append(enemy.Logic.WantsToMove ? 1 : 0).Append(',').Append(distHero.ToString("F2", inv))
                .Append(',').Append(l0).Append(',').Append(w0.ToString("F2", inv)).Append(',').Append(l1).Append(',').Append(w1.ToString("F2", inv)).Append(',').Append(l2).Append(',').Append(w2.ToString("F2", inv))
                .Append(',').Append(offset.ToString("F3", inv))
                .Append(',').Append(agentInfo != null && agentInfo.enabled ? (agentInfo.isOnNavMesh ? "on" : "off") : "none").Append(',').Append(agentInfo != null && agentInfo.enabled ? agentInfo.velocity.magnitude.ToString("F2", inv) : "")
                .Append(',').Append(agentInfo != null && agentInfo.enabled && agentInfo.isOnNavMesh ? agentInfo.pathStatus.ToString() : "").Append(',').Append(agentInfo != null && agentInfo.enabled && agentInfo.isOnNavMesh ? agentInfo.remainingDistance.ToString("F2", inv) : "")
                .Append(',').Append(enemy.Logic.Dormant ? 1 : 0)
                .Append(',').Append(agentInfo != null ? agentInfo.speed.ToString("F2", inv) : "").Append(',').Append(agentInfo != null ? agentInfo.acceleration.ToString("F1", inv) : "")
                .Append(',').Append(enemy.Logic.ChaseSpeed.ToString("F2", inv)).Append(',').Append(enemy.Logic.StopDistance.ToString("F2", inv)).Append('\n');
        }

        IEnumerator RunEnemyScenario(HeroController hero, string mode)
        {
            Directory.CreateDirectory(folder);
            var cam = Camera.main;
            var mixed = mode == "mixed";
            TestSettings.EnemyGodMode = false;
            var host = FindAnyObjectByType<CombatSystemHost>();
            host.Events.Subscribe<SkillPhaseEvent>(OnEnemyPhase);

            EnemyController enemy;
            if (mixed)
            {
                enemy = BusiestEnemy();
                scenarioTarget = null;
            }
            else
            {
                var id = GameFlow.ArgValue("-enemy");
                enemy = FindEnemy(id, hero.transform.position);
                scenarioTarget = enemy;
            }
            if (enemy == null)
            {
                Debug.LogError("[Record] Inimigo não encontrado na cena: " + GameFlow.ArgValue("-enemy"));
                Application.Quit(1);
                yield break;
            }
            enemy.Activate();
            var boss = enemy.Combatant.IsBoss;
            var distance = ArgFloat("-enemydist", mixed ? 5f : boss ? 9f : 6.5f);
            PlaceHeroAtDistance(hero, enemy.transform.position, distance);

            var follow = FindAnyObjectByType<FollowCamera>();
            var followEnemyOnly = string.Equals(GameFlow.ArgValue("-focus"), "enemy", StringComparison.OrdinalIgnoreCase);
            var camSide = string.Equals(GameFlow.ArgValue("-camside"), "1", StringComparison.OrdinalIgnoreCase);
            Transform focus = null;
            if (!mixed && follow != null)
            {
                focus = new GameObject("CamFocus").transform;
                focus.position = (hero.transform.position + enemy.transform.position) * 0.5f;
                follow.SetTarget(focus, true);
            }
            else SnapCamera(hero);
            for (var i = 0; i < 30; i++) yield return null;
            if (focus != null) focus.position = (hero.transform.position + enemy.transform.position) * 0.5f;
            if (follow != null) follow.SetTarget(focus != null ? focus : hero.transform, true);
            traceHero = hero;
            traceEnemy = mixed ? null : enemy;
            if (!hero.Logic.HasKit) Debug.LogError("[Record] O herói não tem kit básico (o roteiro precisa do core nativo).");

            Time.captureFramerate = Fps;
            var maxSeconds = ArgFloat("-maxseconds", mixed ? 40f : boss ? 80f : 32f);
            var script = EnemySteps(hero, mixed, maxSeconds);
            Func<bool> wait = null;
            var done = false;
            var tail = 0;
            for (frame = 0; frame < Mathf.RoundToInt(maxSeconds * Fps); frame++)
            {
                for (var i = tapRelease.Count - 1; i >= 0; i--)
                {
                    if (frame < tapRelease[i].frame) continue;
                    Release(tapRelease[i].command);
                    tapRelease.RemoveAt(i);
                }
                if (!done && (wait == null || wait()))
                {
                    if (script.MoveNext()) wait = script.Current;
                    else done = true;
                }
                if (done && ++tail > 20) break;

                var target = mixed ? NearestEnemy(hero.transform.position) : enemy;
                var aimWorld = target != null ? target.transform.position : hero.transform.position + hero.transform.forward * 3f;
                var screen = cam.WorldToScreenPoint(aimWorld);
                Aim = new Vector2(screen.x, screen.y);
                Move = Vector2.zero;
                if (approachRange > 0f && target != null)
                {
                    var toTarget = target.transform.position - hero.transform.position;
                    toTarget.y = 0f;
                    if (toTarget.magnitude > approachRange) Move = ScreenDirection(cam, toTarget.normalized);
                }
                if (focus != null && enemy != null)
                {
                    // -focus enemy: a camera segue so o inimigo (revisao do clipe de perto); padrao = meio entre o heroi e o inimigo.
                    var goal = followEnemyOnly ? enemy.transform.position : (hero.transform.position + enemy.transform.position) * 0.5f;
                    focus.position = Vector3.Lerp(focus.position, goal, 0.2f);
                    if (camSide && follow != null)
                    {
                        // -camside: camera de lado (perpendicular a linha inimigo-heroi) para ler o golpe de perfil.
                        var line = hero.transform.position - enemy.transform.position;
                        line.y = 0f;
                        if (line.sqrMagnitude > 0.01f)
                        {
                            var yaw = Mathf.Atan2(line.x, line.z) * Mathf.Rad2Deg + 90f;
                            var current = follow.transform.eulerAngles;
                            follow.transform.rotation = Quaternion.Euler(current.x, Mathf.LerpAngle(current.y, yaw, 0.15f), 0f);
                        }
                    }
                }

                yield return new WaitForEndOfFrame();
                SaveFrame(frame);
                EnemyTraceRow(frame);
            }
            Time.captureFramerate = 0;
            host.Events.Unsubscribe<SkillPhaseEvent>(OnEnemyPhase);
            File.WriteAllText(Path.Combine(folder, "trace.csv"), trace.ToString());
            File.WriteAllText(Path.Combine(folder, "trace_enemy.csv"), enemyTrace.ToString());
            Encode(Path.Combine(folder, (string.IsNullOrEmpty(videoName) ? "inimigo" : videoName) + ".mp4"));
            Debug.Log("[Record] roteiro " + mode + ": " + frame + " quadros");
        }

        IEnumerator<Func<bool>> EnemySteps(HeroController hero, bool mixed, float maxSeconds)
        {
            if (!mixed)
            {
                // 1) o herói espera parado: o inimigo vem, telegrafa e ataca (2 golpes ou 10 s).
                var until = frame + 10 * Fps;
                yield return Until(() => enemyImpacts >= 2 || frame >= until);
                yield return Sec(0.6f);
            }
            // 2) o herói luta (combo de 3, forte carregado em rodadas alternadas) até o alvo morrer.
            var rounds = 0;
            var maxFrames = Mathf.RoundToInt(maxSeconds * Fps) - 3 * Fps;
            while (frame < maxFrames)
            {
                var target = NearestEnemy(hero.transform.position);
                if (target == null || target.Combatant == null || target.Combatant.IsDead) break;
                var close = Approach(hero, 1.6f);
                while (close.MoveNext()) yield return close.Current;
                for (var i = 0; i < 3; i++)
                {
                    if (target.Combatant.IsDead) break;
                    var strike = Strike(hero);
                    while (strike.MoveNext()) yield return strike.Current;
                }
                if (target.Combatant.IsDead) break;
                if (rounds % 2 == 1)
                {
                    var heavy = Charge(hero, 1.1f);
                    while (heavy.MoveNext()) yield return heavy.Current;
                }
                else yield return Sec(0.35f);
                rounds++;
            }
            yield return Sec(2.5f); // a queda e o dissolve do inimigo morto
        }

        static float ArgFloat(string name, float fallback)
        {
            var value = GameFlow.ArgValue(name);
            return value != null && float.TryParse(value, System.Globalization.NumberStyles.Float, System.Globalization.CultureInfo.InvariantCulture, out var parsed) ? parsed : fallback;
        }
    }
}
