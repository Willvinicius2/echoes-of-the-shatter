using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using Echoes.Presentation;
using UnityEditor;
using UnityEditor.Animations;
using UnityEngine;

namespace Echoes.EditorTools
{
    /// <summary>
    /// Animator Controllers (AC_Warrior, AC_EnemyHumanoid, AC_Boss) e os SO_SkillPresentation_* que os ligam às habilidades do core. O Animator
    /// NUNCA decide regra: o <c>PresentationController</c> escreve <c>Speed</c>, <c>IsDead</c>, <c>IsStaggered</c>, <c>ActionSpeed</c> e toca os estados
    /// da camada Action a partir dos eventos do combate; os controllers só têm estados e transições de volta ao repouso.
    ///
    /// Estrutura (docs/04, 3.3 e Assets/Scripts/README, seção 5): camada Base (Locomotion = blend de Idle, Walk e Run pela velocidade; Death por
    /// IsDead; Stun por IsStaggered), camada Action (Empty + os golpes e a esquiva, com a velocidade em <c>ActionSpeed</c>) e camada Hit
    /// (Empty + Hit). Clipe que o KayKit não tem vira estado com clipe PLACEHOLDER (tag "Placeholder") e entra na lista de pedidos de Mixamo/Blender.
    /// </summary>
    public static class AnimatorControllerBuilder
    {
        public const string ControllerDir = "Assets/Art/Animations/Controllers";
        public const string SkillSetDir = "Assets/Data/Presentation";
        public const string PlaceholderTag = "Placeholder";

        public sealed class ActionSpec
        {
            public string State;
            public string Fbx;        // caminho do FBX do KayKit
            public string Clip;       // take
            public string SkillId;    // vazio = sem habilidade (esquiva, rugido)
            public bool Placeholder;  // o KayKit nao tem o clipe certo
            public string Note;
        }

        public sealed class ControllerSpec
        {
            public string Name;
            public string SkillSet;           // nome do SO_SkillPresentation_*
            public string Rig;                // "Medium" ou "Large"
            public string SpeedSourceId;      // id em class_stats.csv (heroi) ou enemies.csv
            public bool Hero;
            public string HitClip, DeathClip, StunClip;
            public bool StunPlaceholder;
            public List<ActionSpec> Actions = new List<ActionSpec>();
        }

        static string Medium(string group) => $"{KayKitAnimationImport.Root}/Medium/Rig_Medium_{group}.fbx";
        static string Large(string group) => $"{KayKitAnimationImport.Root}/Large/Rig_Large_{group}.fbx";

        public static readonly ControllerSpec Warrior = new ControllerSpec
        {
            Name = "AC_Warrior", SkillSet = "SO_SkillPresentation_Warrior", Rig = "Medium", SpeedSourceId = "class.warrior", Hero = true,
            HitClip = "Hit_A", DeathClip = "Death_A", StunClip = "Hit_B", StunPlaceholder = true,
            Actions =
            {
                new ActionSpec { State = "Basic", Fbx = Medium("CombatMelee"), Clip = "Melee_1H_Attack_Slice_Horizontal", SkillId = "skill.warrior.iron_cut" },
                new ActionSpec { State = "Charge", Fbx = Medium("CombatMelee"), Clip = "Melee_1H_Attack_Stab", SkillId = "skill.warrior.charge" },
                new ActionSpec { State = "Rift", Fbx = Medium("CombatMelee"), Clip = "Melee_2H_Attack_Chop", SkillId = "skill.warrior.stone_rift" },
                new ActionSpec { State = "Bash", Fbx = Medium("CombatMelee"), Clip = "Melee_Block_Attack", SkillId = "skill.warrior.shield_bash" },
                new ActionSpec { State = "Dodge", Fbx = Medium("MovementAdvanced"), Clip = "Dodge_Forward", SkillId = "" },
            },
        };

        public static readonly ControllerSpec EnemyHumanoid = new ControllerSpec
        {
            Name = "AC_EnemyHumanoid", SkillSet = "SO_SkillPresentation_EnemyHumanoid", Rig = "Medium", SpeedSourceId = "enemy.hollow_sentinel", Hero = false,
            HitClip = "Hit_A", DeathClip = "Death_B", StunClip = "Hit_B", StunPlaceholder = true,
            Actions =
            {
                new ActionSpec { State = "Strike", Fbx = Medium("CombatMelee"), Clip = "Melee_1H_Attack_Chop", SkillId = "skill.enemy.sentinel_strike" },
                new ActionSpec { State = "Slam", Fbx = Medium("CombatMelee"), Clip = "Melee_2H_Attack_Chop", SkillId = "skill.enemy.herald_slam" },
            },
        };

        public static readonly ControllerSpec Boss = new ControllerSpec
        {
            Name = "AC_Boss", SkillSet = "SO_SkillPresentation_Boss", Rig = "Large", SpeedSourceId = "enemy.crypt_guardian", Hero = false,
            HitClip = "Hit_A", DeathClip = "Death_A", StunClip = "Hit_A", StunPlaceholder = true,
            Actions =
            {
                new ActionSpec { State = "Hammer", Fbx = Medium("CombatMelee"), Clip = "Melee_2H_Attack_Chop", SkillId = "skill.enemy.guardian_hammer", Note = "O Melee_2H_Slam do rig grande mergulha o corpo na horizontal (clipe de bruto curvado); o chop do rig medio, retargetado, mantem o chefe em pe" },
                new ActionSpec { State = "ShieldBash", Fbx = Large("CombatMelee"), Clip = "Melee_Block_Attack", SkillId = "skill.enemy.guardian_shield_bash" },
                new ActionSpec { State = "Charge", Fbx = Large("MovementBasic"), Clip = "Running_A", SkillId = "skill.enemy.guardian_shield_charge", Placeholder = true, Note = "Investida do Escudo: o rig grande nao tem avanco com escudo" },
                new ActionSpec { State = "Roar", Fbx = Large("Simulation"), Clip = "Flexing", SkillId = "", Placeholder = true, Note = "Rugido de fase: nao ha rugido no KayKit" },
            },
        };

        public static readonly ControllerSpec[] All = { Warrior, EnemyHumanoid, Boss };

        /// <summary>Clipes que ficaram com placeholder (viram pedido de Mixamo ou de animacao no Blender): "AC_Boss/Roar", "AC_Warrior/Stun"...</summary>
        public static readonly List<string> PlaceholderReport = new List<string>();

        [MenuItem("Echoes/Montar Animator Controllers")]
        public static void BuildAll()
        {
            KayKitAnimationImport.Apply();
            SandboxBuilder.EnsureDir(ControllerDir);
            PlaceholderReport.Clear();
            foreach (var spec in All) BuildController(spec);
            AssetDatabase.SaveAssets();
        }

        public static string ControllerPath(string name) => $"{ControllerDir}/{name}.controller";

        public static RuntimeAnimatorController Load(string name) => AssetDatabase.LoadAssetAtPath<RuntimeAnimatorController>(ControllerPath(name));

        static string Group(string clip)
        {
            return clip;
        }

        static AnimationClip Clip(string fbx, string clip)
        {
            var c = KayKitAnimationImport.FindClip(fbx, clip);
            if (c == null) throw new InvalidOperationException($"Clipe '{clip}' ausente em {fbx} (rode Echoes/Importar animacoes KayKit)");
            return c;
        }

        public static AnimatorController BuildController(ControllerSpec spec)
        {
            var path = ControllerPath(spec.Name);
            if (File.Exists(Path.GetFullPath(Path.Combine(Application.dataPath, "../" + path)))) AssetDatabase.DeleteAsset(path);
            var c = AnimatorController.CreateAnimatorControllerAtPath(path);

            c.AddParameter("Speed", AnimatorControllerParameterType.Float);
            c.AddParameter(new AnimatorControllerParameter { name = "ActionSpeed", type = AnimatorControllerParameterType.Float, defaultFloat = 1f });
            c.AddParameter("IsDead", AnimatorControllerParameterType.Bool);
            c.AddParameter("IsStaggered", AnimatorControllerParameterType.Bool);
            if (spec == Boss) c.AddParameter("Phase", AnimatorControllerParameterType.Int);

            var general = spec.Rig == "Large" ? Large("General") : Medium("General");
            var basic = spec.Rig == "Large" ? Large("MovementBasic") : Medium("MovementBasic");

            // ---- Base: Locomotion (blend pela velocidade), Death, Stun
            var sm = c.layers[0].stateMachine;
            var tree = new BlendTree { name = "Locomotion", blendType = BlendTreeType.Simple1D, blendParameter = "Speed", useAutomaticThresholds = false };
            AssetDatabase.AddObjectToAsset(tree, c);
            var run = MoveSpeedMeters(spec);
            var walk = spec.Hero ? run * 0.5f : run;     // o heroi tem uma velocidade so (corrida); o inimigo anda na dele
            if (!spec.Hero) run = walk * 2f;
            tree.AddChild(Clip(general, "Idle_A"), 0f);
            tree.AddChild(Clip(basic, "Walking_A"), walk);
            tree.AddChild(Clip(basic, "Running_A"), run);
            var loco = sm.AddState("Locomotion");
            loco.motion = tree;
            sm.defaultState = loco;

            var death = sm.AddState("Death");
            death.motion = Clip(general, spec.DeathClip);
            var stun = sm.AddState("Stun");
            stun.motion = Clip(general, spec.StunClip);
            if (spec.StunPlaceholder)
            {
                stun.tag = PlaceholderTag;
                PlaceholderReport.Add($"{spec.Name}/Stun");
            }

            var toDeath = sm.AddAnyStateTransition(death);
            toDeath.AddCondition(AnimatorConditionMode.If, 0f, "IsDead");
            toDeath.hasExitTime = false;
            toDeath.hasFixedDuration = true;
            toDeath.duration = 0.1f;
            toDeath.canTransitionToSelf = false;
            var fromDeath = death.AddTransition(loco);
            fromDeath.AddCondition(AnimatorConditionMode.IfNot, 0f, "IsDead");
            fromDeath.hasExitTime = false;
            fromDeath.duration = 0.1f;

            var toStun = sm.AddAnyStateTransition(stun);
            toStun.AddCondition(AnimatorConditionMode.If, 0f, "IsStaggered");
            toStun.AddCondition(AnimatorConditionMode.IfNot, 0f, "IsDead");
            toStun.hasExitTime = false;
            toStun.hasFixedDuration = true;
            toStun.duration = 0.1f;
            toStun.canTransitionToSelf = false;
            var fromStun = stun.AddTransition(loco);
            fromStun.AddCondition(AnimatorConditionMode.IfNot, 0f, "IsStaggered");
            fromStun.hasExitTime = false;
            fromStun.duration = 0.1f;

            // ---- Action: Empty + golpes e esquiva
            c.AddLayer("Action");
            var layers = c.layers;
            layers[1].defaultWeight = 1f;
            c.layers = layers;
            var actionMachine = c.layers[1].stateMachine;
            var empty = actionMachine.AddState("Empty");
            actionMachine.defaultState = empty;
            foreach (var action in spec.Actions)
            {
                var state = actionMachine.AddState(action.State);
                state.motion = Clip(action.Fbx, action.Clip);
                state.speedParameterActive = true;
                state.speedParameter = "ActionSpeed";
                if (action.Placeholder)
                {
                    state.tag = PlaceholderTag;
                    PlaceholderReport.Add($"{spec.Name}/{action.State}");
                }
                var back = state.AddTransition(empty);
                back.hasExitTime = true;
                back.exitTime = 1f;
                back.hasFixedDuration = true;
                back.duration = 0.08f;
            }

            // ---- Hit: Empty + Hit
            c.AddLayer("Hit");
            layers = c.layers;
            layers[2].defaultWeight = 1f;
            c.layers = layers;
            var hitMachine = c.layers[2].stateMachine;
            var hitEmpty = hitMachine.AddState("Empty");
            hitMachine.defaultState = hitEmpty;
            var hit = hitMachine.AddState("Hit");
            hit.motion = Clip(general, spec.HitClip);
            var hitBack = hit.AddTransition(hitEmpty);
            hitBack.hasExitTime = true;
            hitBack.exitTime = 1f;
            hitBack.hasFixedDuration = true;
            hitBack.duration = 0.08f;

            EditorUtility.SetDirty(c);
            return c;
        }

        // Velocidade de movimento em m/s: class_stats.csv (heroi, em uu/s) ou enemies.csv (inimigo, em uu/s); 1 uu = 1 cm.
        static float MoveSpeedMeters(ControllerSpec spec)
        {
            var dir = Path.GetFullPath(Path.Combine(Application.dataPath, "../Content/Data"));
            string file = spec.Hero ? "class_stats.csv" : "enemies.csv";
            var lines = File.ReadAllLines(Path.Combine(dir, file));
            var header = lines[0].Split(',');
            foreach (var line in lines.Skip(1))
            {
                var cells = line.Split(',');
                if (spec.Hero)
                {
                    if (cells[0] == spec.SpeedSourceId && cells[1] == "move_speed") return float.Parse(cells[2], CultureInfo.InvariantCulture) / 100f;
                }
                else if (cells[0] == spec.SpeedSourceId)
                {
                    return float.Parse(cells[Array.IndexOf(header, "moveSpeed")], CultureInfo.InvariantCulture) / 100f;
                }
            }
            throw new InvalidOperationException($"Velocidade de {spec.SpeedSourceId} nao encontrada em {file}");
        }

        // ============================================================================================== SO_SkillPresentation_*

        public static SkillPresentationSet BuildSkillSet(ControllerSpec spec, GameObject prefab)
        {
            SandboxBuilder.EnsureDir(SkillSetDir);
            var set = SandboxBuilder.LoadOrCreate<SkillPresentationSet>($"{SkillSetDir}/{spec.SkillSet}.asset");
            set.entries.Clear();
            var instance = (GameObject)PrefabUtility.InstantiatePrefab(prefab);
            try
            {
                foreach (var action in spec.Actions)
                {
                    if (string.IsNullOrEmpty(action.SkillId)) continue;
                    var clip = Clip(action.Fbx, action.Clip);
                    ClipTiming.Analyze(instance, clip, out var windupEnd, out var impactEnd);
                    set.entries.Add(new SkillPresentationEntry
                    {
                        skillId = action.SkillId, animatorState = action.State, clipSeconds = clip.length,
                        windupEnd = windupEnd, impactEnd = impactEnd, anchor = "socket_weapon_r",
                    });
                }
            }
            finally
            {
                UnityEngine.Object.DestroyImmediate(instance);
            }
            set.dodgeState = "Dodge";
            EditorUtility.SetDirty(set);
            return set;
        }

        public static string SkillSetPathFor(string enemyId)
        {
            switch (enemyId)
            {
                case "enemy.hollow_sentinel":
                case "enemy.shielded_sentinel":
                case "enemy.stone_herald":
                    return $"{SkillSetDir}/{EnemyHumanoid.SkillSet}.asset";
                case "enemy.crypt_guardian":
                    return $"{SkillSetDir}/{Boss.SkillSet}.asset";
                default:
                    return null;
            }
        }

        public static string WarriorSkillSetPath => $"{SkillSetDir}/{Warrior.SkillSet}.asset";
    }

    /// <summary>
    /// Instante do golpe no clipe: amostra o clipe no personagem e mede a velocidade da mão da arma (RightHand/LeftHand). A preparação termina
    /// quando a mão acelera (40% do pico) e o impacto quando ela volta a desacelerar. O PresentationController escala a velocidade do clipe
    /// para a preparação e o impacto do core (seção 3.3). Sem movimento detectável, valores padrão.
    /// </summary>
    public static class ClipTiming
    {
        public const float DefaultWindupEnd = 0.35f;
        public const float DefaultImpactEnd = 0.6f;

        public static void Analyze(GameObject instance, AnimationClip clip, out float windupEnd, out float impactEnd)
        {
            windupEnd = DefaultWindupEnd;
            impactEnd = DefaultImpactEnd;
            var hands = new List<Transform>();
            foreach (var name in new[] { "RightHand", "LeftHand" })
            {
                var t = CharacterPrefabBuilder.FindDeep(instance.transform, name);
                if (t != null) hands.Add(t);
            }
            if (hands.Count == 0 || clip.length < 0.1f) return;

            const float fps = 60f;
            var steps = Mathf.CeilToInt(clip.length * fps);
            var speeds = new float[steps];
            var previous = new Vector3[hands.Count];
            for (var i = 0; i <= steps; i++)
            {
                clip.SampleAnimation(instance, Mathf.Min(clip.length, i / fps));
                var best = 0f;
                for (var h = 0; h < hands.Count; h++)
                {
                    var p = hands[h].position;
                    if (i > 0) best = Mathf.Max(best, (p - previous[h]).magnitude * fps);
                    previous[h] = p;
                }
                if (i > 0) speeds[i - 1] = best;
            }
            var peak = speeds.Max();
            if (peak < 0.5f) return; // a mao quase nao se mexe: mantem o padrao
            var limit = 0.4f * peak;
            var first = Array.FindIndex(speeds, s => s >= limit);
            var last = Array.FindLastIndex(speeds, s => s >= limit);
            if (first < 0 || last <= first) return;
            windupEnd = Mathf.Clamp(first / (float)steps, 0.05f, 0.9f);
            impactEnd = Mathf.Clamp((last + 1) / (float)steps, windupEnd + 0.05f, 1f);
        }
    }
}
