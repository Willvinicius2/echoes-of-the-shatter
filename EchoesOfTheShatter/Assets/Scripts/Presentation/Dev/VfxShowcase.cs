using System;
using System.Collections;
using System.Collections.Generic;
using System.Diagnostics;
using System.Globalization;
using System.IO;
using System.Reflection;
using System.Text;
using Echoes.Core;
using Echoes.Gameplay;
using Echoes.Interop;
using UnityEngine;
using Debug = UnityEngine.Debug;

namespace Echoes.Presentation
{
    /// <summary>
    /// SÓ DESENVOLVIMENTO: vitrine dos VFX das habilidades (<c>-vfxshow PASTA</c>). Monta bonecos de treino e dispara cada efeito pelo caminho real:
    /// publica os mesmos <see cref="SkillPhaseEvent"/> e <see cref="BasicInputEvent"/> que a lógica de combate publica, lança os projéteis no
    /// <see cref="ProjectileSystem"/> do <see cref="CombatSystem"/> e resolve os golpes com <c>ApplySkillHit</c> (motor de regras de verdade). Quem
    /// desenha são os presenters do jogo (<see cref="SkillVfxPresenter"/>, <see cref="ProjectilePresenter"/>, <see cref="PresentationController"/>),
    /// lendo os SO_SkillPresentation_*. Assim dá para mostrar a Bola de Fogo e a flecha mesmo antes de class.archer e class.mage existirem no core:
    /// a habilidade que não está no skills.csv vem do <c>VfxShowcase.json</c> (docs/18 seção 2, só para a vitrine).
    /// Grava PNG/JPG a 30 fps (<c>Time.captureFramerate</c>) por habilidade e por enquadramento (de perto e na câmera do jogo a 56 m), junta em MP4
    /// com o ffmpeg do PATH e anota os quadros-chave em <c>marks.txt</c>. Inerte sem o argumento; nunca roda no jogo normal.
    /// <para>Argumentos: <c>-vfxshow PASTA</c>, <c>-vfxonly id1,id2</c> (filtra), <c>-vfxviews perto,56m</c>.</para>
    /// </summary>
    [DisallowMultipleComponent]
    public sealed class VfxShowcase : MonoBehaviour
    {
        const int Fps = 30;

        [SerializeField] GameRoot root;
        [SerializeField] CombatSystemHost host;
        [SerializeField] VfxPool pool;
        [SerializeField] SkillVfxPresenter presenter;
        [SerializeField] Camera viewCamera;
        [SerializeField] RenderSettingsAsset renderSettings;
        [SerializeField] TextAsset script;
        [Tooltip("Volume global com bloom leve; peso 1 nos enquadramentos terminados em _bloom.")]
        [SerializeField] UnityEngine.Rendering.Volume bloomVolume;
        [Header("Modelos prontos (objeto inativo com AttributeComponent + PresentationController + corpo)")]
        [SerializeField] GameObject warriorTemplate;
        [SerializeField] GameObject archerTemplate;
        [SerializeField] GameObject mageTemplate;
        [SerializeField] GameObject dummyTemplate;
        [SerializeField] GameObject ghostTemplate;

        sealed class SkillDef
        {
            public string Id;
            public SkillInfo Info;
            public float CorridorMeters;
            public bool Line;
            public float ShotRangeMeters;
        }

        sealed class Shot
        {
            public string Id, Caster, SkillId, Kind, TargetKind;
            public float Charge, Tail, FrameHeight;
            public bool AimAtTargets;
            public List<Vector2> Targets = new List<Vector2>();
        }

        sealed class Stage
        {
            public Combatant Caster;
            public Transform CasterTransform;
            public readonly List<Combatant> Targets = new List<Combatant>();
            public readonly List<GameObject> Objects = new List<GameObject>();
            public Vector3 AimDirection;
            public Vector3 AimRight;
        }

        readonly Dictionary<string, SkillDef> sims = new Dictionary<string, SkillDef>(StringComparer.Ordinal);
        readonly List<Shot> shots = new List<Shot>();
        sealed class TimedAction
        {
            public float Time;
            public Action Run;
            public bool Fired;
        }

        readonly List<TimedAction> timeline = new List<TimedAction>();
        readonly List<HitEvent> stepHits = new List<HitEvent>();
        readonly StringBuilder marks = new StringBuilder();
        IRulesCore rules;
        CombatSystem combat;
        Stage stage;
        SkillDef activeDef;
        int frameIndex;
        bool subscribed;
        string failure;

        // -------------------------------------------------------------------------------------------------------------- arranque

        static string ArgValue(string name)
        {
            var args = Environment.GetCommandLineArgs();
            for (var i = 0; i < args.Length - 1; i++)
            {
                if (string.Equals(args[i], name, StringComparison.OrdinalIgnoreCase)) return args[i + 1];
            }
            return null;
        }

        IEnumerator Start()
        {
            var folder = ArgValue("-vfxshow");
            if (string.IsNullOrEmpty(folder)) yield break;
            var only = ArgValue("-vfxonly");
            var views = ArgValue("-vfxviews") ?? "perto,56m,56m_bloom";
            yield return RunScript(folder, only, views);
            Time.captureFramerate = 0;
            Quit(failure == null ? 0 : 1);
        }

        void Quit(int code)
        {
            if (failure != null) Debug.LogError("[VfxShow] FALHOU: " + failure);
#if UNITY_EDITOR
            UnityEditor.SessionState.SetInt("echoes.vfxshow.exit", code);
            UnityEditor.EditorApplication.isPlaying = false;
#else
            Application.Quit(code);
#endif
        }

        /// <summary>Último erro da vitrine (null = tudo certo).</summary>
        public string Failure => failure;

        /// <summary>Roda o roteiro (todas as habilidades ou as de <paramref name="only"/>) nos enquadramentos de <paramref name="viewList"/> ("perto,56m"). Os testes de Play chamam por aqui.</summary>
        public IEnumerator RunScript(string folder, string only, string viewList)
        {
            Directory.CreateDirectory(folder);
            for (var i = 0; i < 6; i++) yield return null; // GameRoot, CombatSystemHost e presenters acordam
            if (root == null || !root.IsReady || host == null || host.Combat == null || presenter == null || pool == null)
            {
                failure = "cena da vitrine incompleta (GameRoot/Combat/VfxPool/SkillVfxPresenter) ou regras nao carregaram";
                yield break;
            }
            rules = root.Rules.Core;
            combat = host.Combat;
            Subscribe();
            try
            {
                ParseScript();
            }
            catch (Exception e)
            {
                failure = "roteiro: " + e;
                yield break;
            }

            var filter = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            if (!string.IsNullOrEmpty(only)) foreach (var id in only.Split(',')) filter.Add(id.Trim());
            var viewNames = viewList.Split(',');

            Time.captureFramerate = Fps;
            foreach (var shot in shots)
            {
                if (filter.Count > 0 && !filter.Contains(shot.Id)) continue;
                foreach (var view in viewNames)
                {
                    var name = view.Trim();
                    yield return RecordShot(shot, name, folder);
                    if (failure != null) yield break;
                }
            }
            File.WriteAllText(Path.Combine(folder, "marks.txt"), marks.ToString());
        }

        void Subscribe()
        {
            if (subscribed) return;
            root.Events.Subscribe<HitEvent>(OnHit);
            root.Events.Subscribe<ProjectileEvent>(OnProjectile);
            subscribed = true;
        }

        void OnDestroy()
        {
            if (!subscribed || root == null || root.Events == null) return;
            root.Events.Unsubscribe<HitEvent>(OnHit);
            root.Events.Unsubscribe<ProjectileEvent>(OnProjectile);
        }

        // -------------------------------------------------------------------------------------------------------------- roteiro (JSON)

        void ParseScript()
        {
            var doc = MiniJson.AsObject(MiniJson.Parse(script.text));
            foreach (var item in MiniJson.AsArray(doc["skills"]))
            {
                var o = MiniJson.AsObject(item);
                var def = new SkillDef
                {
                    Id = MiniJson.Str(o, "id"),
                    CorridorMeters = (float)MiniJson.Num(o, "corridorUu", 20) * 0.01f,
                    Line = MiniJson.Bool(o, "line"),
                    ShotRangeMeters = (float)MiniJson.Num(o, "shotRangeUu", 0) * 0.01f,
                };
                def.Info = rules.FindSkill(def.Id) ?? MakeSkill(o);
                sims[def.Id] = def;
            }
            foreach (var item in MiniJson.AsArray(doc["shots"]))
            {
                var o = MiniJson.AsObject(item);
                var shot = new Shot
                {
                    Id = MiniJson.Str(o, "id"), Caster = MiniJson.Str(o, "caster"), SkillId = MiniJson.Str(o, "skill"), Kind = MiniJson.Str(o, "kind", "skill"),
                    TargetKind = MiniJson.Str(o, "targetKind", "dummy"), Charge = (float)MiniJson.Num(o, "charge"), Tail = (float)MiniJson.Num(o, "tail", 1.2),
                    FrameHeight = (float)MiniJson.Num(o, "frameHeight", 10), AimAtTargets = MiniJson.Bool(o, "aimAtTargets"),
                };
                foreach (var t in MiniJson.AsArray(o["targets"]))
                {
                    var pair = MiniJson.AsArray(t);
                    shot.Targets.Add(new Vector2((float)(double)pair[0], (float)(double)pair[1]));
                }
                if (!string.IsNullOrEmpty(shot.SkillId) && !sims.ContainsKey(shot.SkillId))
                {
                    // Habilidade real do CSV (Corte de Ferro, flecha do Fantasma) que o roteiro não redefine.
                    var info = rules.FindSkill(shot.SkillId);
                    if (info == null) throw new InvalidOperationException("Habilidade sem linha no CSV nem no roteiro: " + shot.SkillId);
                    sims[shot.SkillId] = new SkillDef { Id = shot.SkillId, Info = info, CorridorMeters = 0.1f };
                }
                shots.Add(shot);
            }
        }

        static void SetProp(object target, string name, object value)
        {
            typeof(SkillInfo).GetProperty(name, BindingFlags.Public | BindingFlags.Instance).GetSetMethod(true).Invoke(target, new[] { value });
        }

        // Habilidade só da vitrine: monta o SkillInfo (setters internos do Interop) com os valores do roteiro.
        static SkillInfo MakeSkill(Dictionary<string, object> o)
        {
            var info = new SkillInfo();
            SetProp(info, "Id", MiniJson.Str(o, "id"));
            SetProp(info, "Shape", Enum.Parse(typeof(SkillShape), MiniJson.Str(o, "shape"), true));
            SetProp(info, "Tags", ParseTags(MiniJson.Str(o, "tags")));
            SetProp(info, "Windup", MiniJson.Num(o, "windup"));
            SetProp(info, "Impact", MiniJson.Num(o, "impact"));
            SetProp(info, "Recovery", MiniJson.Num(o, "recovery"));
            SetProp(info, "RangeUu", MiniJson.Num(o, "rangeUu"));
            SetProp(info, "RadiusUu", MiniJson.Num(o, "radiusUu"));
            SetProp(info, "ConeAngleDegrees", MiniJson.Num(o, "coneDegrees"));
            SetProp(info, "ProjectileSpeedUu", MiniJson.Num(o, "speedUu"));
            SetProp(info, "Projectiles", Math.Max(1, MiniJson.Int(o, "projectiles", 1)));
            SetProp(info, "BaseDamage", new DamageByType
            {
                Physical = MiniJson.Num(o, "physical"), Fire = MiniJson.Num(o, "fire"), Cold = MiniJson.Num(o, "cold"), Lightning = MiniJson.Num(o, "lightning"),
            });
            return info;
        }

        static SkillTags ParseTags(string text)
        {
            var result = SkillTags.None;
            foreach (var part in text.Split('|'))
            {
                if (Enum.TryParse<SkillTags>(part.Trim(), true, out var tag)) result |= tag;
            }
            return result;
        }

        // -------------------------------------------------------------------------------------------------------------- eventos do combate

        void OnHit(in HitEvent evt)
        {
            if (evt.Skill == null) return;
            stepHits.Add(evt);
            if (marks.Length == 0 || !currentMarkHit)
            {
                currentMarkHit = true;
                Mark("acerto");
            }
        }

        bool currentMarkHit;

        void OnProjectile(in ProjectileEvent evt)
        {
            if (evt.Spawned || stage == null) return;
            // A explosao em area e a perfuracao sao da logica (ProjectileSystem); aqui so se marca o quadro para a prancha.
            if (evt.ExplosionRadiusMeters <= 0f) return;
            Mark("explosao");
        }

        void Mark(string name)
        {
            marks.AppendLine($"{currentShotLabel}\t{name}\t{frameIndex}");
        }

        string currentShotLabel = string.Empty;

        /// <summary>Picos medidos na última habilidade gravada (orçamento: luzes pontuais, partículas vivas e efeitos tocando).</summary>
        public int PeakLights { get; private set; }
        public int PeakParticles { get; private set; }
        public int PeakEffects { get; private set; }

        void SampleBudget()
        {
            var lights = 0;
            foreach (var lamp in FindObjectsByType<Light>(FindObjectsSortMode.None))
            {
                if (lamp.enabled && lamp.type == LightType.Point && lamp.intensity > 0.05f) lights++;
            }
            var particles = 0;
            foreach (var system in FindObjectsByType<ParticleSystem>(FindObjectsSortMode.None)) particles += system.particleCount;
            PeakLights = Mathf.Max(PeakLights, lights);
            PeakParticles = Mathf.Max(PeakParticles, particles);
            PeakEffects = Mathf.Max(PeakEffects, pool.ActiveCount);
        }

        // -------------------------------------------------------------------------------------------------------------- palco

        ClassInfo ClassFor(string classId)
        {
            var info = rules.FindClass(classId);
            if (info != null) return info;
            // class.archer / class.mage ainda não estão no CSV: clone da classe do Guerreiro com outro ID, para o ContentId (e as chaves do kit) bater.
            var warrior = rules.FindClass("class.warrior");
            var clone = new ClassInfo();
            foreach (var prop in typeof(ClassInfo).GetProperties(BindingFlags.Public | BindingFlags.Instance))
            {
                var setter = prop.GetSetMethod(true);
                if (setter != null) setter.Invoke(clone, new[] { prop.GetValue(warrior) });
            }
            typeof(ClassInfo).GetProperty("Id").GetSetMethod(true).Invoke(clone, new object[] { classId });
            return clone;
        }

        GameObject Spawn(GameObject template, Vector3 position, Vector3 facing)
        {
            var go = Instantiate(template, position, Quaternion.LookRotation(facing, Vector3.up));
            go.name = template.name.Replace("Template_", string.Empty);
            go.SetActive(true);
            return go;
        }

        Combatant MakeHero(string casterKind, Vector3 position, Vector3 facing, Stage s)
        {
            string classId;
            GameObject template;
            switch (casterKind)
            {
                case "archer": classId = "class.archer"; template = archerTemplate; break;
                case "mage": classId = "class.mage"; template = mageTemplate; break;
                default: classId = "class.warrior"; template = warriorTemplate; break;
            }
            var go = Spawn(template, position, facing);
            s.Objects.Add(go);
            var attributes = go.GetComponent<AttributeComponent>();
            var build = new HeroBuild("class.warrior", 5, new[] { "item_base.iron_sword" });
            var combatant = attributes.CreateHero(rules, in build, ClassFor(classId), rules.FindItemBase("item_base.iron_sword"), 0.3f);
            combat.Register(combatant, null);
            combatant.Position = position.ToPlanar();
            combatant.Forward = facing.ToPlanar().NormalizedOr(PlanarVector.Forward);
            return combatant;
        }

        Combatant MakeEnemy(string enemyId, GameObject template, Vector3 position, Vector3 facing, Stage s)
        {
            var go = Spawn(template, position, facing);
            s.Objects.Add(go);
            var attributes = go.GetComponent<AttributeComponent>();
            var info = rules.FindEnemy(enemyId);
            var combatant = attributes.CreateEnemy(rules, info, 3, 0.5f);
            combat.Register(combatant, null);
            combatant.Position = position.ToPlanar();
            combatant.Forward = facing.ToPlanar().NormalizedOr(PlanarVector.Forward);
            return combatant;
        }

        Stage BuildStage(Shot shot)
        {
            var s = new Stage();
            // Direção da mira: para a direita da tela (perfil), um pouco para cima, para o voo do projétil aparecer inteiro.
            var yaw = renderSettings != null ? renderSettings.yawDegrees : 45f;
            var camRot = Quaternion.Euler(0f, yaw, 0f);
            var right = camRot * Vector3.right;
            var forward = camRot * Vector3.forward;
            s.AimDirection = (right + forward * 0.28f).normalized;
            s.AimRight = Vector3.Cross(Vector3.up, s.AimDirection).normalized * -1f; // lateral à direita de quem olha ao longo da mira
            var origin = Vector3.zero;
            if (shot.Caster == "ghost") s.Caster = MakeEnemy("enemy.ghost_archer", ghostTemplate, origin, s.AimDirection, s);
            else s.Caster = MakeHero(shot.Caster, origin, s.AimDirection, s);
            s.CasterTransform = (s.Caster.Owner as Component).transform;
            foreach (var t in shot.Targets)
            {
                var position = origin + s.AimDirection * t.x + s.AimRight * t.y;
                var face = -s.AimDirection;
                Combatant target;
                if (shot.TargetKind == "warrior") target = MakeHero("warrior", position, face, s);
                else target = MakeEnemy("enemy.hollow_sentinel", dummyTemplate, position, face, s);
                s.Targets.Add(target);
            }
            return s;
        }

        void ClearStage()
        {
            if (stage == null) return;
            combat.Projectiles.Clear(combat);
            foreach (var c in stage.Targets) combat.Unregister(c);
            combat.Unregister(stage.Caster);
            foreach (var go in stage.Objects) Destroy(go);
            stage = null;
            activeDef = null;
        }

        // -------------------------------------------------------------------------------------------------------------- câmera e captura

        void FrameCamera(string view, Shot shot)
        {
            var s = renderSettings;
            var rotation = Quaternion.Euler(s.pitchDegrees, s.yawDegrees, 0f);
            Vector3 focus;
            float distance, fov;
            if (view == "56m")
            {
                // A câmera do jogo: o herói no centro, 56 m, FOV 14,2 (FollowCamera).
                focus = stage.CasterTransform.position + s.targetOffset;
                distance = s.distance;
                fov = s.verticalFieldOfView;
            }
            else
            {
                var sum = stage.CasterTransform.position;
                var count = 1;
                foreach (var t in stage.Targets) { sum += ((Component)t.Owner).transform.position; count++; }
                focus = sum / count + Vector3.up * 0.7f;
                distance = 24f;
                fov = 2f * Mathf.Atan(shot.FrameHeight * 0.5f / distance) * Mathf.Rad2Deg;
            }
            viewCamera.transform.SetPositionAndRotation(focus - rotation * Vector3.forward * distance, rotation);
            viewCamera.fieldOfView = fov;
            viewCamera.nearClipPlane = s.nearClip;
            viewCamera.farClipPlane = s.farClip;
        }

        IEnumerator RecordShot(Shot shot, string view, string folder)
        {
            var bloom = view.EndsWith("_bloom", StringComparison.Ordinal);
            if (bloom) view = view.Substring(0, view.Length - "_bloom".Length);
            if (bloomVolume != null) bloomVolume.weight = bloom ? 1f : 0f;
            var label = $"{shot.Id}_{view}{(bloom ? "_bloom" : string.Empty)}";
            currentShotLabel = label;
            currentMarkHit = false;
            var frames = Path.Combine(folder, "frames", label);
            if (Directory.Exists(frames)) Directory.Delete(frames, true);
            Directory.CreateDirectory(frames);

            PeakLights = 0;
            PeakParticles = 0;
            PeakEffects = 0;
            stage = BuildStage(shot);
            presenter.AimResolver = owner =>
            {
                if (!ReferenceEquals(owner, stage.Caster)) return null;
                return AimPoint(shot);
            };
            timeline.Clear();
            stepHits.Clear();
            var duration = BuildTimeline(shot);
            FrameCamera(view, shot);

            var width = view == "56m" ? 1920 : 1280;
            var height = view == "56m" ? 1080 : 720;
            var rt = new RenderTexture(width, height, 24, RenderTextureFormat.ARGB32) { antiAliasing = 1 }; // o MSAA vem do URP asset
            var read = new Texture2D(width, height, TextureFormat.RGB24, false);
            viewCamera.targetTexture = rt;
            viewCamera.enabled = false; // renderizamos a mao no fim do quadro: sem depender da janela Game (modo batch)

            // Quadros de assentamento (Animator em repouso, pools aquecidos) antes de gravar.
            for (var i = 0; i < 12; i++) yield return null;
            frameIndex = 0;
            var elapsed = 0f;
            var total = duration + shot.Tail;
            var frameCount = Mathf.CeilToInt(total * Fps);
            for (frameIndex = 0; frameIndex < frameCount; frameIndex++)
            {
                failure = RunDue(elapsed, label);
                if (failure != null) yield break;
                if (frameIndex % 2 == 0) SampleBudget();
                yield return new WaitForEndOfFrame();
                viewCamera.Render();
                RenderTexture.active = rt;
                read.ReadPixels(new Rect(0, 0, width, height), 0, 0, false);
                read.Apply(false);
                RenderTexture.active = null;
                File.WriteAllBytes(Path.Combine(frames, $"{frameIndex:D5}.jpg"), read.EncodeToJPG(94));
                elapsed += 1f / Fps;
                stepHits.Clear(); // as acertadas por passo servem so a explosao do mesmo passo
            }

            viewCamera.targetTexture = null;
            viewCamera.enabled = true;
            Destroy(rt);
            Destroy(read);
            ClearStage();
            presenter.AimResolver = null;
            for (var i = 0; i < 4; i++) yield return null;
            Encode(frames, Path.Combine(folder, label + ".mp4"));
            marks.AppendLine($"{label}	orcamento	luzes={PeakLights} particulas={PeakParticles} efeitos={PeakEffects}");
            Debug.Log($"[VfxShow] {label}: {frameCount} quadros, picos: luzes {PeakLights}, particulas {PeakParticles}, efeitos {PeakEffects}");
        }

        // Dispara o que venceu; ações novas (o tiro do salto) entram na mesma lista. Devolve o erro, se houver (sem yield dentro de catch).
        string RunDue(float elapsed, string label)
        {
            for (var i = 0; i < timeline.Count; i++)
            {
                var item = timeline[i];
                if (item.Fired || item.Time > elapsed + 1e-4f) continue;
                item.Fired = true;
                try
                {
                    item.Run();
                }
                catch (Exception e)
                {
                    return label + ": " + e;
                }
            }
            return null;
        }

        static void Encode(string frames, string mp4)
        {
            try
            {
                var info = new ProcessStartInfo("ffmpeg", $"-y -loglevel error -framerate {Fps} -i \"{Path.Combine(frames, "%05d.jpg")}\" -c:v libx264 -pix_fmt yuv420p -crf 17 -preset medium \"{mp4}\"")
                {
                    UseShellExecute = false, CreateNoWindow = true, RedirectStandardError = true,
                };
                using (var process = Process.Start(info))
                {
                    var error = process.StandardError.ReadToEnd();
                    process.WaitForExit();
                    if (process.ExitCode != 0) Debug.LogError("[VfxShow] ffmpeg: " + error);
                }
            }
            catch (Exception e)
            {
                Debug.LogError("[VfxShow] ffmpeg indisponivel: " + e.Message);
            }
        }

        PlanarVector AimPoint(Shot shot)
        {
            var origin = stage.Caster.Position;
            if (shot.AimAtTargets && stage.Targets.Count > 0)
            {
                var sum = PlanarVector.Zero;
                foreach (var t in stage.Targets) sum += t.Position;
                return sum * (1f / stage.Targets.Count);
            }
            if (stage.Targets.Count > 0) return stage.Targets[0].Position;
            return origin + stage.AimDirection.ToPlanar() * 5f;
        }

        // -------------------------------------------------------------------------------------------------------------- roteiro de uma habilidade

        void At(float time, Action action) => timeline.Add(new TimedAction { Time = time, Run = action });

        void Publish(SkillInfo skill, ActionPhase phase, double seconds)
        {
            var direction = (AimPoint(currentShot) - stage.Caster.Position).NormalizedOr(stage.Caster.Forward);
            var evt = new SkillPhaseEvent { Owner = stage.Caster, Skill = skill, Phase = phase, PhaseSeconds = seconds, Direction = direction };
            combat.Events.Publish(in evt);
        }

        void PublishInput(BasicInputKind kind, SkillInfo skill, double value = 0.0)
        {
            var evt = new BasicInputEvent { Owner = stage.Caster, Kind = kind, Skill = skill, Value = value };
            combat.Events.Publish(in evt);
        }

        Shot currentShot;

        // Devolve a duração da parte "ativa" (antes da cauda). O tempo 0,45 s é o repouso inicial do quadro.
        float BuildTimeline(Shot shot)
        {
            currentShot = shot;
            const float lead = 0.45f;
            if (shot.Kind == "guard") return BuildGuard(shot, lead, false);
            if (shot.Kind == "barrier") return BuildGuard(shot, lead, true);

            var def = sims[shot.SkillId];
            activeDef = def;
            var skill = def.Info;
            var t = lead;
            if (shot.Charge > 0f)
            {
                At(t, () => { Mark("carga_inicio"); PublishInput(BasicInputKind.ChargeStarted, skill); });
                At(t + shot.Charge, () => { Mark("carga_maxima"); PublishInput(BasicInputKind.ChargeFull, skill); });
                At(t + shot.Charge + 0.1f, () => PublishInput(BasicInputKind.HeavyReleased, skill, 2.0));
                t += shot.Charge + 0.1f;
            }
            var windup = (float)skill.Windup;
            var impact = (float)skill.Impact;
            var recovery = (float)skill.Recovery;
            At(t, () => { Mark("preparacao"); Publish(skill, ActionPhase.Windup, windup); });
            At(t + windup, () => { Mark("saida"); Publish(skill, ActionPhase.Impact, impact); Effect(def, shot); });
            At(t + windup + impact, () => Publish(skill, ActionPhase.Recovery, recovery));
            At(t + windup + impact + recovery, () => Publish(skill, ActionPhase.None, 0.0));
            return t + windup + impact + recovery;
        }

        PlanarVector AimCenter(SkillDef def)
        {
            var toAim = AimPoint(currentShot) - stage.Caster.Position;
            return stage.Caster.Position + toAim.ClampMagnitude(WorldUnits.ToMeters(def.Info.RangeUu));
        }

        void Effect(SkillDef def, Shot shot)
        {
            var skill = def.Info;
            var caster = stage.Caster;
            var direction = (AimPoint(shot) - caster.Position).NormalizedOr(caster.Forward);
            switch (skill.Shape)
            {
                case SkillShape.Melee:
                case SkillShape.Cone:
                {
                    var range = WorldUnits.ToMeters(skill.RangeUu);
                    var half = (float)(skill.ConeAngleDegrees * 0.5);
                    foreach (var target in stage.Targets)
                    {
                        if (!target.IsDead && ShapeQuery.InCone(caster.Position, direction, range, half, target.Position, target.RadiusMeters))
                            combat.ApplySkillHit(caster, target, skill, caster.Position);
                    }
                    break;
                }
                case SkillShape.Projectile:
                    SpawnShots(def, caster.Position, direction);
                    break;
                case SkillShape.Dash:
                {
                    // Salto para trás: recua `rangeUu` durante o impacto e atira no pico.
                    var back = -direction;
                    var distance = WorldUnits.ToMeters(skill.RangeUu);
                    StartCoroutine(Leap(back, distance, (float)skill.Impact));
                    At(TimeNow() + (float)skill.Impact * 0.5f, () => SpawnShots(def, caster.Position, direction));
                    break;
                }
                case SkillShape.Area:
                    if (def.Line)
                    {
                        var end = caster.Position + direction * WorldUnits.ToMeters(skill.RangeUu);
                        foreach (var target in stage.Targets)
                        {
                            if (!target.IsDead && ShapeQuery.InCorridor(caster.Position, end, WorldUnits.ToMeters(skill.RadiusUu), target.Position, target.RadiusMeters))
                                combat.ApplySkillHit(caster, target, skill, caster.Position);
                        }
                    }
                    else if (skill.Behavior.GroundTargeted)
                    {
                        // Como a logica: o circulo fica onde o cursor estava e o golpe sai ao fim do impacto.
                        var center = AimCenter(def);
                        At(TimeNow() + (float)skill.Impact, () => HitCircle(def, center, WorldUnits.ToMeters(skill.RadiusUu)));
                    }
                    else if (skill.RangeUu <= 0.0 || skill.Behavior.SelfCentered) HitCircle(def, caster.Position, WorldUnits.ToMeters(skill.RadiusUu));
                    break;
            }
        }

        float TimeNow() => frameIndex / (float)Fps;

        void HitCircle(SkillDef def, PlanarVector center, float radius)
        {
            foreach (var target in stage.Targets)
            {
                if (!target.IsDead && ShapeQuery.InCircle(center, radius, target.Position, target.RadiusMeters))
                    combat.ApplySkillHit(stage.Caster, target, def.Info, center);
            }
        }

        void SpawnShots(SkillDef def, PlanarVector origin, PlanarVector direction)
        {
            var skill = def.Info;
            var count = Math.Max(1, skill.Projectiles);
            var spread = (float)skill.ConeAngleDegrees;
            var range = def.ShotRangeMeters > 0f ? def.ShotRangeMeters : WorldUnits.ToMeters(skill.RangeUu);
            for (var i = 0; i < count; i++)
            {
                // Leque: ConeAngle graus divididos entre as flechas (docs/18 8.3b: o core ainda não define; a vitrine abre o leque).
                var angle = count > 1 && (skill.Behavior.Fan || spread > 0f) ? Mathf.Lerp(-spread * 0.5f, spread * 0.5f, i / (float)(count - 1)) : 0f;
                var rotated = Quaternion.Euler(0f, angle, 0f) * new Vector3(direction.X, 0f, direction.Z);
                combat.Projectiles.Spawn(combat, stage.Caster, skill, origin, rotated.ToPlanar(), WorldUnits.ToMeters(skill.ProjectileSpeedUu), range, ProjectileSystem.BodyRadiusMeters(skill));
            }
        }

        IEnumerator Leap(PlanarVector back, float distance, float seconds)
        {
            var start = stage.Caster.Position;
            var caster = stage.Caster;
            var t = stage.CasterTransform;
            var elapsed = 0f;
            while (elapsed < seconds && stage != null && ReferenceEquals(stage.Caster, caster))
            {
                elapsed += Time.deltaTime;
                var k = Mathf.Clamp01(elapsed / seconds);
                caster.Position = start + back * (distance * k);
                t.position = caster.Position.ToWorld(0f);
                yield return null;
            }
        }

        float BuildGuard(Shot shot, float lead, bool barrier)
        {
            var caster = stage.Caster;
            var contactFront = stage.CasterTransform.position + stage.AimDirection * 0.7f + Vector3.up * 1.0f;
            At(lead, () => { Mark("defesa_ergue"); PublishInput(BasicInputKind.GuardUp, null); });
            if (!barrier)
            {
                At(lead + 0.7f, () => { Mark("bloqueio"); presenter.GuardBlock(caster, contactFront); });
                At(lead + 1.3f, () => { Mark("defesa_perfeita"); presenter.GuardPerfect(caster, contactFront); });
                At(lead + 1.9f, () => PublishInput(BasicInputKind.GuardDown, null));
                return lead + 1.9f;
            }
            var right = stage.AimRight;
            At(lead + 0.7f, () => { Mark("onda_1"); presenter.GuardBlock(caster, stage.CasterTransform.position + (stage.AimDirection * 0.7f + right * 0.5f).normalized * 1.1f + Vector3.up * 1.1f); });
            At(lead + 1.0f, () => presenter.GuardBlock(caster, stage.CasterTransform.position + (-stage.AimDirection * 0.6f + right * 0.8f).normalized * 1.1f + Vector3.up * 1.3f));
            At(lead + 1.3f, () => presenter.GuardBlock(caster, stage.CasterTransform.position + (stage.AimDirection + Vector3.up * 0.6f).normalized * 1.1f + Vector3.up * 1.0f));
            At(lead + 2.0f, () => { Mark("estilhaca"); PublishInput(BasicInputKind.GuardBroke, null); });
            return lead + 2.0f;
        }
    }
}
