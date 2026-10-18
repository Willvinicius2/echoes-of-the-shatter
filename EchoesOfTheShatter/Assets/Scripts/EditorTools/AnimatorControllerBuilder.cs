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

        /// <summary>Saída das camadas Action e Hit para o repouso (0,12 a 0,18 s): a locomoção volta sem corte.</summary>
        public const float ExitBlendSeconds = 0.15f;

        public sealed class ActionSpec
        {
            public string State;
            public string Fbx;        // caminho do FBX do KayKit
            public string Clip;       // take
            public string SkillId;    // vazio = sem habilidade (esquiva, rugido)
            public bool Placeholder;  // o KayKit nao tem o clipe certo
            public string Note;
            public bool Hold;         // sem saida automatica para Empty (laco ou fase que o core encerra)
            public string[] AlsoSkills; // outras habilidades que tocam o mesmo estado (cada uma ganha a propria entrada)
            public float Lunge;       // peso: avanco visual do corpo no impacto (m), so no filho visual; arte, nao regra
            public bool HoldPose;     // golpe carregado: o quadro "arma atras" (holdAt) e medido no clipe; a preparacao do golpe comeca nele
        }

        /// <summary>Estado da camada de tronco e bracos (mascara AM_UpperBody): defesa e carga, enquanto as pernas andam na camada Base.</summary>
        public sealed class UpperSpec
        {
            public string State;
            public string Fbx;
            public string Clip;
            public string Next;       // estado para onde vai ao terminar o clipe (vazio = segura o ultimo quadro)
            public bool TimeParam;    // o tempo do clipe e o parametro HoldAt (pose congelada)
            public float Speed = 1f;  // velocidade de reproducao do estado (erguer a defesa e armar a carga sao curtos: docs/18, 5.1)
            public float ExitTime = 1f; // fracao do clipe em que passa para Next (o clipe chega na pose final antes do fim: medido com DevPipeline.Diagnose)
            public float FreezeAt;    // > 0: estado parado (velocidade 0) neste ponto normalizado do clipe, para segurar a pose enquanto o botao esta apertado
        }

        /// <summary>Golpe em fases (preparacao, impacto e recuperacao em estados separados, cada um com o seu clipe): usa estados de Actions.</summary>
        public sealed class PhaseSkillSpec
        {
            public string SkillId;
            public string WindupState;
            public string ImpactState;
            public string RecoveryState;
            public float WindupFrom;      // trecho do clipe da preparacao que toca (fracao): o puxar da corda, nao o clipe inteiro (medido com DevPipeline.Diagnose)
            public float WindupTo = 1f;
        }

        public sealed class ControllerSpec
        {
            public string Name;
            public string SkillSet;           // nome do SO_SkillPresentation_*
            public string Rig;                // "Medium" ou "Large"
            public string SpeedSourceId;      // id em class_stats.csv (heroi) ou enemies.csv
            public bool Hero;
            public string HitClip, DeathClip;
            public List<ActionSpec> Actions = new List<ActionSpec>();
            // Locomocao do heroi (docs/18, 5): o Guerreiro corre com Running_A, o Arqueiro com Running_HoldingBow e o Mago com Running_B.
            public string WalkClip = "Walking_A";
            public string RunFbx;     // vazio = MovementBasic do rig
            public string RunClip = "Running_A";
            public List<UpperSpec> Upper = new List<UpperSpec>();
            public List<PhaseSkillSpec> PhaseSkills = new List<PhaseSkillSpec>();
            public string ChargeState = "ChargeHold";       // primeiro estado da camada Upper ao carregar
            public string GuardRaiseState = "GuardRaise";
            public string GuardHitState = "GuardHit";       // vazio = a defesa nao tem reacao propria
        }

        /// <summary>
        /// Erguer a defesa (Melee_Block) chega na pose de Melee_Blocking em 0,333 s (31% do clipe, medido); passa para o laco ai e toca a 2x
        /// (0,17 s de entrada), para a defesa parecer firme e nao um levantar lento. Arte, nao balanceamento.
        /// </summary>
        public const float BlockPoseTime = 0.313f, GuardRaiseSpeed = 2f;

        public const string UpperLayerName = "Upper";
        public const string UpperMaskPath = ControllerDir + "/AM_UpperBody.mask";

        static string Medium(string group) => $"{KayKitAnimationImport.Root}/Medium/Rig_Medium_{group}.fbx";
        static string Large(string group) => $"{KayKitAnimationImport.Root}/Large/Rig_Large_{group}.fbx";

        public static readonly ControllerSpec Warrior = new ControllerSpec
        {
            Name = "AC_Warrior", SkillSet = "SO_SkillPresentation_Warrior", Rig = "Medium", SpeedSourceId = "class.warrior", Hero = true,
            HitClip = "Hit_A", DeathClip = "Death_A",
            RunClip = WarriorRunClip(),
            Actions =
            {
                // Combo (docs/18, 5.1): cada golpe e um clipe diferente do anterior
                new ActionSpec { State = "Basic", Fbx = Medium("CombatMelee"), Clip = "Melee_1H_Attack_Slice_Horizontal", SkillId = "skill.warrior.iron_cut", Lunge = 0.12f },
                new ActionSpec { State = "Combo2", Fbx = Medium("CombatMelee"), Clip = "Melee_1H_Attack_Slice_Diagonal", SkillId = "skill.warrior.combo_2", Lunge = 0.15f },
                new ActionSpec { State = "Combo3", Fbx = Medium("CombatMelee"), Clip = "Melee_1H_Attack_Jump_Chop", SkillId = "skill.warrior.combo_3", Lunge = 0.3f },
                // Forte: a mesma Melee_2H_Attack_Slice congelada na carga (camada Upper) e solta daqui, do quadro holdAt ate o fim
                new ActionSpec { State = "HeavyRelease", Fbx = Medium("CombatMelee"), Clip = "Melee_2H_Attack_Slice", SkillId = "skill.warrior.heavy_slash", HoldPose = true, Lunge = 0.35f },
                new ActionSpec { State = "Charge", Fbx = Medium("CombatMelee"), Clip = "Melee_1H_Attack_Stab", SkillId = "skill.warrior.charge" },
                new ActionSpec { State = "Rift", Fbx = Medium("CombatMelee"), Clip = "Melee_2H_Attack_Chop", SkillId = "skill.warrior.stone_rift" },
                new ActionSpec { State = "Bash", Fbx = Medium("CombatMelee"), Clip = "Melee_Block_Attack", SkillId = "skill.warrior.shield_bash" },
                new ActionSpec { State = "Dodge", Fbx = Medium("MovementAdvanced"), Clip = "Dodge_Forward", SkillId = "" },
            },
            Upper =
            {
                new UpperSpec { State = "GuardRaise", Fbx = Medium("CombatMelee"), Clip = "Melee_Block", Next = "GuardHold", Speed = GuardRaiseSpeed, ExitTime = BlockPoseTime },
                new UpperSpec { State = "GuardHold", Fbx = Medium("CombatMelee"), Clip = "Melee_Blocking" },
                new UpperSpec { State = "GuardHit", Fbx = Medium("CombatMelee"), Clip = "Melee_Block_Hit", Next = "GuardHold" },
                new UpperSpec { State = "ChargeHold", Fbx = Medium("CombatMelee"), Clip = "Melee_2H_Attack_Slice", TimeParam = true },
            },
        };

        // Corrida do Guerreiro: Running_A, ou Running_B para comparar em video (ECHOES_WARRIOR_RUN=Running_B; so no editor, ao montar).
        static string WarriorRunClip()
        {
            var env = Environment.GetEnvironmentVariable("ECHOES_WARRIOR_RUN");
            return string.IsNullOrEmpty(env) ? "Running_A" : env;
        }

        /// <summary>Arqueiro (docs/18, 5.2): disparo curto = Draw na preparacao + Release; carga = Draw e depois Aiming_Idle; corre com Running_HoldingBow.</summary>
        public static readonly ControllerSpec HeroArcher = new ControllerSpec
        {
            Name = "AC_Archer", SkillSet = "SO_SkillPresentation_Archer", Rig = "Medium", SpeedSourceId = "class.archer", Hero = true,
            HitClip = "Hit_A", DeathClip = "Death_A",
            RunFbx = Medium("MovementAdvanced"), RunClip = "Running_HoldingBow",
            ChargeState = "ChargeDraw",
            Actions =
            {
                new ActionSpec { State = "BowDraw", Fbx = Medium("CombatRanged"), Clip = "Ranged_Bow_Draw", SkillId = "" },
                new ActionSpec { State = "BowRelease", Fbx = Medium("CombatRanged"), Clip = "Ranged_Bow_Release", SkillId = "skill.archer.piercing_shot" },
                new ActionSpec { State = "RainDraw", Fbx = Medium("CombatRanged"), Clip = "Ranged_Bow_Draw_Up", SkillId = "" },
                new ActionSpec { State = "RainRelease", Fbx = Medium("CombatRanged"), Clip = "Ranged_Bow_Release_Up", SkillId = "" },
                new ActionSpec { State = "BackLeap", Fbx = Medium("MovementAdvanced"), Clip = "Dodge_Backward", SkillId = "skill.archer.back_leap" },
                new ActionSpec { State = "Dodge", Fbx = Medium("MovementAdvanced"), Clip = "Dodge_Forward", SkillId = "" },
            },
            PhaseSkills =
            {
                new PhaseSkillSpec { SkillId = "skill.archer.quick_shot", WindupState = "BowDraw", ImpactState = "BowRelease", WindupFrom = 0.33f, WindupTo = 0.62f }, // Bow_Draw: ajusta a flecha em 0,44 s e puxa ate 0,83 s (62%)
                new PhaseSkillSpec { SkillId = "skill.archer.fan_shot", WindupState = "BowDraw", ImpactState = "BowRelease", WindupFrom = 0.15f, WindupTo = 0.62f },
                new PhaseSkillSpec { SkillId = "skill.archer.arrow_rain", WindupState = "RainDraw", ImpactState = "RainRelease", WindupFrom = 0.15f, WindupTo = 0.62f },
            },
            Upper =
            {
                new UpperSpec { State = "GuardRaise", Fbx = Medium("CombatMelee"), Clip = "Melee_Block", Next = "GuardHold", Speed = GuardRaiseSpeed, ExitTime = BlockPoseTime },
                new UpperSpec { State = "GuardHold", Fbx = Medium("CombatMelee"), Clip = "Melee_Blocking" },
                new UpperSpec { State = "GuardHit", Fbx = Medium("CombatMelee"), Clip = "Melee_Block_Hit", Next = "GuardHold" },
                new UpperSpec { State = "ChargeDraw", Fbx = Medium("CombatRanged"), Clip = "Ranged_Bow_Draw", Next = "ChargeHold", Speed = 1.25f, ExitTime = 0.65f }, // a puxada assenta na mira em 65% do clipe (medido)
                new UpperSpec { State = "ChargeHold", Fbx = Medium("CombatRanged"), Clip = "Ranged_Bow_Aiming_Idle" },
            },
        };

        /// <summary>Mago (docs/18, 5.3): Dardo = Shoot; Orbe e Raio = Spellcasting na preparacao + Shoot; carga = Spellcasting_Long; defesa = Raise congelado no ultimo quadro.</summary>
        public static readonly ControllerSpec HeroMage = new ControllerSpec
        {
            Name = "AC_Mage", SkillSet = "SO_SkillPresentation_Mage", Rig = "Medium", SpeedSourceId = "class.mage", Hero = true,
            HitClip = "Hit_A", DeathClip = "Death_A",
            RunClip = "Running_B",
            GuardHitState = "",
            Actions =
            {
                new ActionSpec { State = "MageShoot", Fbx = Medium("CombatRanged"), Clip = "Ranged_Magic_Shoot", SkillId = "skill.mage.arcane_dart", AlsoSkills = new[] { "skill.mage.fireball" } },
                new ActionSpec { State = "MageCast", Fbx = Medium("CombatRanged"), Clip = "Ranged_Magic_Spellcasting", SkillId = "" },
                new ActionSpec { State = "MageSummon", Fbx = Medium("CombatRanged"), Clip = "Ranged_Magic_Summon", SkillId = "skill.mage.frost_nova" },
                new ActionSpec { State = "Dodge", Fbx = Medium("MovementAdvanced"), Clip = "Dodge_Forward", SkillId = "" },
            },
            PhaseSkills =
            {
                new PhaseSkillSpec { SkillId = "skill.mage.arcane_orb", WindupState = "MageCast", ImpactState = "MageShoot" },
                new PhaseSkillSpec { SkillId = "skill.mage.arcane_ray", WindupState = "MageCast", ImpactState = "MageShoot" },
            },
            Upper =
            {
                // Raise: os bracos chegam na pose em 0,67 s (32% do clipe) e o resto do clipe baixa de novo; a pose fica parada enquanto segura.
                new UpperSpec { State = "GuardRaise", Fbx = Medium("CombatRanged"), Clip = "Ranged_Magic_Raise", Next = "GuardHold", Speed = 2f, ExitTime = 0.32f },
                new UpperSpec { State = "GuardHold", Fbx = Medium("CombatRanged"), Clip = "Ranged_Magic_Raise", FreezeAt = 0.32f },
                // Spellcasting_Long: o armar vai ate ~1,3 s (51%), depois vem o gesto de lancar (so no solto); a carga para o armar nessa pose.
                new UpperSpec { State = "ChargeHold", Fbx = Medium("CombatRanged"), Clip = "Ranged_Magic_Spellcasting_Long", Next = "ChargeFreeze", Speed = 1.6f, ExitTime = 0.5f },
                new UpperSpec { State = "ChargeFreeze", Fbx = Medium("CombatRanged"), Clip = "Ranged_Magic_Spellcasting_Long", FreezeAt = 0.5f },
            },
        };

        public static readonly ControllerSpec EnemyHumanoid = new ControllerSpec
        {
            Name = "AC_EnemyHumanoid", SkillSet = "SO_SkillPresentation_EnemyHumanoid", Rig = "Medium", SpeedSourceId = "enemy.hollow_sentinel", Hero = false,
            HitClip = "Hit_A", DeathClip = "Death_B",
            Actions =
            {
                new ActionSpec { State = "Strike", Fbx = Medium("CombatMelee"), Clip = "Melee_1H_Attack_Chop", SkillId = "skill.enemy.sentinel_strike" },
                new ActionSpec { State = "Slam", Fbx = Medium("CombatMelee"), Clip = "Melee_2H_Attack_Chop", SkillId = "skill.enemy.herald_slam" },
            },
        };

        public static readonly ControllerSpec Boss = new ControllerSpec
        {
            Name = "AC_Boss", SkillSet = "SO_SkillPresentation_Boss", Rig = "Large", SpeedSourceId = "enemy.crypt_guardian", Hero = false,
            HitClip = "Hit_A", DeathClip = "Death_A",
            Actions =
            {
                new ActionSpec { State = "Hammer", Fbx = Medium("CombatMelee"), Clip = "Melee_2H_Attack_Chop", SkillId = "skill.enemy.guardian_hammer", Note = "O Melee_2H_Slam do rig grande mergulha o corpo na horizontal (clipe de bruto curvado); o chop do rig medio, retargetado, mantem o chefe em pe" },
                new ActionSpec { State = "ShieldBash", Fbx = Large("CombatMelee"), Clip = "Melee_Block_Attack", SkillId = "skill.enemy.guardian_shield_bash" },
                // Investida do Escudo (fase 2): preparacao, corrida em laco e recuperacao, cada uma com o seu clipe (golpes do Blender).
                new ActionSpec { State = "ChargeWindup", Fbx = EchoesAnimationImport.PathOf(EchoesAnimationImport.ChargeWindupName), Clip = EchoesAnimationImport.ChargeWindupName, SkillId = "", Hold = true },
                new ActionSpec { State = "ChargeRun", Fbx = EchoesAnimationImport.PathOf(EchoesAnimationImport.ChargeRunName), Clip = EchoesAnimationImport.ChargeRunName, SkillId = "", Hold = true },
                new ActionSpec { State = "ChargeRecover", Fbx = EchoesAnimationImport.PathOf(EchoesAnimationImport.ChargeRecoverName), Clip = EchoesAnimationImport.ChargeRecoverName, SkillId = "" },
                new ActionSpec { State = "Roar", Fbx = EchoesAnimationImport.PathOf(EchoesAnimationImport.RoarName), Clip = EchoesAnimationImport.RoarName, SkillId = "" },
            },
        };

        public static readonly ControllerSpec[] All = { Warrior, EnemyHumanoid, Boss, HeroArcher, HeroMage };

        /// <summary>Clipes que ficaram com placeholder (viram pedido de Mixamo ou de animacao no Blender): "AC_Boss/Roar", "AC_Warrior/Stun"...</summary>
        public static readonly List<string> PlaceholderReport = new List<string>();

        [MenuItem("Echoes/Montar Animator Controllers")]
        public static void BuildAll()
        {
            KayKitAnimationImport.Apply();
            EchoesAnimationImport.Apply();
            SandboxBuilder.EnsureDir(ControllerDir);
            PlaceholderReport.Clear();
            foreach (var spec in All) BuildController(spec);
            BuildArcherController();
            BuildHoundController();
            AssetDatabase.SaveAssets();
            // Recria e recarrega: sem isso o Load logo depois pode devolver null no mesmo quadro do editor.
            foreach (var spec in All) AssetDatabase.ImportAsset(ControllerPath(spec.Name), ImportAssetOptions.ForceUpdate);
            AssetDatabase.ImportAsset(ControllerPath(ArcherControllerName), ImportAssetOptions.ForceUpdate);
            AssetDatabase.ImportAsset(ControllerPath(HoundControllerName), ImportAssetOptions.ForceUpdate);
        }

        public static string ControllerPath(string name) => $"{ControllerDir}/{name}.controller";

        public static RuntimeAnimatorController Load(string name)
        {
            var path = ControllerPath(name);
            var controller = AssetDatabase.LoadAssetAtPath<RuntimeAnimatorController>(path);
            if (controller == null)
            {
                AssetDatabase.ImportAsset(path, ImportAssetOptions.ForceUpdate);
                controller = AssetDatabase.LoadAssetAtPath<RuntimeAnimatorController>(path);
            }
            return controller;
        }

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
            if (spec.Upper.Count > 0) c.AddParameter("HoldAt", AnimatorControllerParameterType.Float); // tempo normalizado da pose de carga congelada

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
            tree.AddChild(Clip(basic, spec.WalkClip), walk);
            tree.AddChild(Clip(spec.RunFbx ?? basic, spec.RunClip), run);
            ApplyGroundSpeedScales(tree, spec.Name, walk, run);
            var loco = sm.AddState("Locomotion");
            loco.motion = tree;
            sm.defaultState = loco;
            if (spec.Hero) BuildAimLocomotion(c, sm, loco, Clip(general, "Idle_A"), Clip(basic, spec.WalkClip), walk);

            var death = sm.AddState("Death");
            death.motion = Clip(general, spec.DeathClip);
            var stun = sm.AddState("Stun");
            stun.motion = EchoesAnimationImport.Clip(EchoesAnimationImport.StunName); // clipe do Blender (Humanoid, serve a todos)

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
                if (action.Hold) continue;
                var back = state.AddTransition(empty);
                back.hasExitTime = true;
                back.exitTime = 1f;
                back.hasFixedDuration = true;
                back.duration = ExitBlendSeconds;
            }

            // ---- Upper (so herois): tronco e bracos com mascara, para defender e carregar enquanto as pernas da camada Base andam
            if (spec.Upper.Count > 0) BuildUpperLayer(c, spec);

            // ---- Hit: Empty + Hit
            c.AddLayer("Hit");
            layers = c.layers;
            var hitIndex = layers.Length - 1;
            layers[hitIndex].defaultWeight = 1f;
            c.layers = layers;
            var hitMachine = c.layers[hitIndex].stateMachine;
            var hitEmpty = hitMachine.AddState("Empty");
            hitMachine.defaultState = hitEmpty;
            var hit = hitMachine.AddState("Hit");
            hit.motion = Clip(general, spec.HitClip);
            var hitBack = hit.AddTransition(hitEmpty);
            hitBack.hasExitTime = true;
            hitBack.exitTime = 1f;
            hitBack.hasFixedDuration = true;
            hitBack.duration = ExitBlendSeconds;

            EditorUtility.SetDirty(c);
            return c;
        }

        public const float StrafePlaybackScale = 0.55f; // docs/18, 5.1: laterais da defesa a 55% de velocidade

        /// <summary>
        /// Pernas de quem defende ou carrega (parametro Aiming): o corpo encara a mira e anda para qualquer lado. Blend 2D pela velocidade local
        /// (MoveX = direita, MoveY = frente, em m/s): frente Walking, recuo Walking_Backwards, lados Running_Strafe a 55%. O tronco e os bracos
        /// ficam na camada Upper.
        /// </summary>
        static void BuildAimLocomotion(AnimatorController c, AnimatorStateMachine sm, AnimatorState loco, AnimationClip idle, AnimationClip walkForward, float walkSpeed)
        {
            c.AddParameter("Aiming", AnimatorControllerParameterType.Bool);
            c.AddParameter("MoveX", AnimatorControllerParameterType.Float);
            c.AddParameter("MoveY", AnimatorControllerParameterType.Float);
            var advanced = Medium("MovementAdvanced");
            var tree = new BlendTree { name = "AimLocomotion", blendType = BlendTreeType.FreeformDirectional2D, blendParameter = "MoveX", blendParameterY = "MoveY", useAutomaticThresholds = false };
            AssetDatabase.AddObjectToAsset(tree, c);
            tree.AddChild(idle, new Vector2(0f, 0f));
            tree.AddChild(walkForward, new Vector2(0f, walkSpeed));
            tree.AddChild(Clip(advanced, "Walking_Backwards"), new Vector2(0f, -walkSpeed));
            tree.AddChild(Clip(advanced, "Running_Strafe_Left"), new Vector2(-walkSpeed, 0f));
            tree.AddChild(Clip(advanced, "Running_Strafe_Right"), new Vector2(walkSpeed, 0f));
            var children = tree.children;
            children[3].timeScale = StrafePlaybackScale;
            children[4].timeScale = StrafePlaybackScale;
            tree.children = children;
            var aim = sm.AddState("AimLocomotion");
            aim.motion = tree;
            var enter = loco.AddTransition(aim);
            enter.AddCondition(AnimatorConditionMode.If, 0f, "Aiming");
            enter.hasExitTime = false;
            enter.hasFixedDuration = true;
            enter.duration = 0.12f;
            var leave = aim.AddTransition(loco);
            leave.AddCondition(AnimatorConditionMode.IfNot, 0f, "Aiming");
            leave.hasExitTime = false;
            leave.hasFixedDuration = true;
            leave.duration = 0.12f;
        }

        // Camada Upper: AvatarMask de tronco, cabeca e bracos (sem raiz nem pernas). Os estados vem de spec.Upper; "Empty" e o repouso.
        static void BuildUpperLayer(AnimatorController c, ControllerSpec spec)
        {
            c.AddLayer(UpperLayerName);
            var layers = c.layers;
            var index = layers.Length - 1;
            layers[index].defaultWeight = 1f;
            layers[index].blendingMode = AnimatorLayerBlendingMode.Override;
            layers[index].avatarMask = LoadOrCreateUpperMask();
            c.layers = layers;
            var machine = c.layers[index].stateMachine;
            var empty = machine.AddState("Empty");
            machine.defaultState = empty;
            var states = new Dictionary<string, AnimatorState>();
            foreach (var upper in spec.Upper)
            {
                var state = machine.AddState(upper.State);
                state.motion = Clip(upper.Fbx, upper.Clip);
                state.speed = upper.FreezeAt > 0f ? 0f : upper.Speed;
                if (upper.FreezeAt > 0f) state.cycleOffset = upper.FreezeAt;
                if (upper.TimeParam)
                {
                    state.timeParameterActive = true;
                    state.timeParameter = "HoldAt";
                }
                states[upper.State] = state;
            }
            foreach (var upper in spec.Upper)
            {
                if (string.IsNullOrEmpty(upper.Next) || !states.TryGetValue(upper.Next, out var next)) continue;
                var t = states[upper.State].AddTransition(next);
                t.hasExitTime = true;
                t.exitTime = upper.ExitTime;
                t.hasFixedDuration = true;
                t.duration = 0.06f;
            }
        }

        static AvatarMask LoadOrCreateUpperMask()
        {
            var mask = AssetDatabase.LoadAssetAtPath<AvatarMask>(UpperMaskPath);
            if (mask == null)
            {
                mask = new AvatarMask { name = "AM_UpperBody" };
                AssetDatabase.CreateAsset(mask, UpperMaskPath);
            }
            foreach (AvatarMaskBodyPart part in Enum.GetValues(typeof(AvatarMaskBodyPart)))
            {
                if (part == AvatarMaskBodyPart.LastBodyPart) continue;
                var upper = part == AvatarMaskBodyPart.Body || part == AvatarMaskBodyPart.Head || part == AvatarMaskBodyPart.LeftArm || part == AvatarMaskBodyPart.RightArm
                    || part == AvatarMaskBodyPart.LeftFingers || part == AvatarMaskBodyPart.RightFingers;
                mask.SetHumanoidBodyPartActive(part, upper);
            }
            EditorUtility.SetDirty(mask);
            return mask;
        }

        /// <summary>
        /// Para o pé acompanhar o chão: o timeScale de Walk e Run na árvore = velocidade do jogo ÷ velocidade de solo medida do clipe
        /// (<see cref="LocomotionGroundSpeed"/>), limitado a 0,75 a 1,35. Sem medida gravada, 1 (como antes).
        /// </summary>
        static void ApplyGroundSpeedScales(BlendTree tree, string controllerName, float walkGameSpeed, float runGameSpeed)
        {
            var measured = LocomotionGroundSpeed.Load(controllerName);
            if (measured == null) return;
            var children = tree.children;
            children[1].timeScale = LocomotionGroundSpeed.PlaybackScale(walkGameSpeed, measured.walk);
            children[2].timeScale = LocomotionGroundSpeed.PlaybackScale(runGameSpeed, measured.run, LocomotionGroundSpeed.RunMaxScale);
            tree.children = children;
        }

        // Velocidade de movimento em m/s: class_stats.csv (heroi, em uu/s) ou enemies.csv (inimigo, em uu/s); 1 uu = 1 cm.
        static float MoveSpeedMeters(ControllerSpec spec)
        {
            // So para o video da corrida: o mesmo override de RecordMode (ECHOES_DEV_HERO_SPEED, m/s) vale no limiar da corrida da arvore do heroi.
            var dev = Environment.GetEnvironmentVariable("ECHOES_DEV_HERO_SPEED");
            if (spec.Hero && !string.IsNullOrEmpty(dev) && float.TryParse(dev, NumberStyles.Float, CultureInfo.InvariantCulture, out var devSpeed) && devSpeed > 0f) return devSpeed;
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
                    var holdAt = 0f;
                    if (action.HoldPose)
                    {
                        holdAt = ClipTiming.FindHoldPose(instance, clip, windupEnd);
                        Debug.Log($"[ClipTiming] {spec.Name}/{action.State}: holdAt {holdAt:F3} (windupEnd {windupEnd:F3}, impactEnd {impactEnd:F3}, clip {clip.length:F2}s)");
                    }
                    var skills = new List<string> { action.SkillId };
                    if (action.AlsoSkills != null) skills.AddRange(action.AlsoSkills);
                    foreach (var skillId in skills)
                    {
                        set.entries.Add(new SkillPresentationEntry
                        {
                            skillId = skillId, animatorState = action.State, clipSeconds = clip.length,
                            windupEnd = windupEnd, impactEnd = impactEnd, holdAt = holdAt, lungeMeters = action.Lunge, anchor = "socket_weapon_r",
                        });
                    }
                }
                foreach (var phase in spec.PhaseSkills)
                {
                    var windup = spec.Actions.Find(a => a.State == phase.WindupState);
                    var impact = string.IsNullOrEmpty(phase.ImpactState) ? null : spec.Actions.Find(a => a.State == phase.ImpactState);
                    var recovery = string.IsNullOrEmpty(phase.RecoveryState) ? null : spec.Actions.Find(a => a.State == phase.RecoveryState);
                    if (windup == null) throw new InvalidOperationException($"{spec.Name}: estado de preparacao '{phase.WindupState}' de {phase.SkillId} nao existe");
                    var windupClip = Clip(windup.Fbx, windup.Clip);
                    var impactClip = impact != null ? Clip(impact.Fbx, impact.Clip) : null;
                    var recoveryClip = recovery != null ? Clip(recovery.Fbx, recovery.Clip) : null;
                    set.entries.Add(new SkillPresentationEntry
                    {
                        skillId = phase.SkillId, animatorState = phase.WindupState, clipSeconds = windupClip.length,
                        windupEnd = 1f, impactEnd = 1f, anchor = "socket_weapon_r",
                        windupState = phase.WindupState, windupClipSeconds = windupClip.length, windupFrom = phase.WindupFrom, windupTo = phase.WindupTo,
                        impactState = phase.ImpactState ?? string.Empty, impactClipSeconds = impactClip != null ? impactClip.length : 0f,
                        recoveryState = phase.RecoveryState ?? string.Empty, recoveryClipSeconds = recoveryClip != null ? recoveryClip.length : 1f,
                    });
                }
            }
            finally
            {
                UnityEngine.Object.DestroyImmediate(instance);
            }
            if (spec == Boss)
            {
                // Investida do Escudo: tres estados, cada um com o clipe e a duracao autoral; o core manda as fases (preparacao, impacto, recuperacao).
                set.entries.Add(new SkillPresentationEntry
                {
                    skillId = "skill.enemy.guardian_shield_charge", animatorState = "ChargeWindup", clipSeconds = EchoesAnimationImport.Spec(EchoesAnimationImport.ChargeWindupName).Seconds,
                    windupState = "ChargeWindup", windupClipSeconds = EchoesAnimationImport.Spec(EchoesAnimationImport.ChargeWindupName).Seconds,
                    impactState = "ChargeRun",
                    recoveryState = "ChargeRecover", recoveryClipSeconds = EchoesAnimationImport.Spec(EchoesAnimationImport.ChargeRecoverName).Seconds,
                    windupEnd = 1f, impactEnd = 1f, anchor = "socket_weapon_r",
                });
            }
            set.dodgeState = "Dodge";
            if (spec.Upper.Count > 0)
            {
                set.upperLayer = UpperLayerName;
                set.guardRaiseState = spec.GuardRaiseState;
                set.guardHitState = spec.GuardHitState;
                set.chargeState = spec.ChargeState;
            }
            EditorUtility.SetDirty(set);
            return set;
        }

        // ============================================================================================== Arqueiro Espectral (Generic)

        public const string ArcherControllerName = "AC_GhostArcher";
        public const string ArcherSkillSetName = "SO_SkillPresentation_GhostArcher";
        public const string ArcherSkillId = "skill.enemy.ghost_arrow";

        /// <summary>
        /// AC_GhostArcher (Generic; golpes do Blender): Base com Idle e Glide (blend pela velocidade) e Death (IsDead), camada Action com Shoot
        /// (velocidade do clipe em ActionSpeed) e camada Hit. O disparo sai no quadro 20 (evento "release"), que o PresentationController casa com o impacto do core.
        /// </summary>
        public static AnimatorController BuildArcherController()
        {
            var path = ControllerPath(ArcherControllerName);
            if (File.Exists(Path.GetFullPath(Path.Combine(Application.dataPath, "../" + path)))) AssetDatabase.DeleteAsset(path);
            var c = AnimatorController.CreateAnimatorControllerAtPath(path);
            c.AddParameter("Speed", AnimatorControllerParameterType.Float);
            c.AddParameter(new AnimatorControllerParameter { name = "ActionSpeed", type = AnimatorControllerParameterType.Float, defaultFloat = 1f });
            c.AddParameter("IsDead", AnimatorControllerParameterType.Bool);

            var sm = c.layers[0].stateMachine;
            var tree = new BlendTree { name = "Locomotion", blendType = BlendTreeType.Simple1D, blendParameter = "Speed", useAutomaticThresholds = false };
            AssetDatabase.AddObjectToAsset(tree, c);
            tree.AddChild(EchoesAnimationImport.Clip("AN_GhostArcher_Idle"), 0f);
            tree.AddChild(EchoesAnimationImport.Clip("AN_GhostArcher_Glide"), MoveSpeedMeters(new ControllerSpec { SpeedSourceId = "enemy.ghost_archer", Hero = false }));
            var loco = sm.AddState("Locomotion");
            loco.motion = tree;
            sm.defaultState = loco;
            var death = sm.AddState("Death");
            death.motion = EchoesAnimationImport.Clip("AN_GhostArcher_Death");
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

            c.AddLayer("Action");
            var layers = c.layers;
            layers[1].defaultWeight = 1f;
            c.layers = layers;
            var action = c.layers[1].stateMachine;
            var empty = action.AddState("Empty");
            action.defaultState = empty;
            var shoot = action.AddState("Shoot");
            shoot.motion = EchoesAnimationImport.Clip("AN_GhostArcher_Shoot");
            shoot.speedParameterActive = true;
            shoot.speedParameter = "ActionSpeed";
            var back = shoot.AddTransition(empty);
            back.hasExitTime = true;
            back.exitTime = 1f;
            back.hasFixedDuration = true;
            back.duration = ExitBlendSeconds;

            c.AddLayer("Hit");
            layers = c.layers;
            layers[2].defaultWeight = 1f;
            c.layers = layers;
            var hitMachine = c.layers[2].stateMachine;
            var hitEmpty = hitMachine.AddState("Empty");
            hitMachine.defaultState = hitEmpty;
            var hit = hitMachine.AddState("Hit");
            hit.motion = EchoesAnimationImport.Clip("AN_GhostArcher_Hit");
            var hitBack = hit.AddTransition(hitEmpty);
            hitBack.hasExitTime = true;
            hitBack.exitTime = 1f;
            hitBack.hasFixedDuration = true;
            hitBack.duration = ExitBlendSeconds;
            EditorUtility.SetDirty(c);
            return c;
        }

        // ============================================================================================== Cao de Cinza (Generic quadrupede)

        public const string HoundControllerName = "AC_Hound";
        public const string HoundSkillSetName = "SO_SkillPresentation_Hound";
        public const string HoundSkillId = "skill.enemy.ash_bite";

        /// <summary>
        /// AC_Hound: Base com Locomotion (Idle, Walk e Run pela velocidade), Flee (a fuga do core: IsFleeing) e Death; camada Action com Bite (velocidade do
        /// clipe em ActionSpeed, casada com preparacao/impacto/recuperacao do core) e camada Hit.
        /// </summary>
        public static AnimatorController BuildHoundController()
        {
            var path = ControllerPath(HoundControllerName);
            if (File.Exists(Path.GetFullPath(Path.Combine(Application.dataPath, "../" + path)))) AssetDatabase.DeleteAsset(path);
            var c = AnimatorController.CreateAnimatorControllerAtPath(path);
            c.AddParameter("Speed", AnimatorControllerParameterType.Float);
            c.AddParameter(new AnimatorControllerParameter { name = "ActionSpeed", type = AnimatorControllerParameterType.Float, defaultFloat = 1f });
            c.AddParameter("IsDead", AnimatorControllerParameterType.Bool);
            c.AddParameter("IsFleeing", AnimatorControllerParameterType.Bool);

            var sm = c.layers[0].stateMachine;
            var tree = new BlendTree { name = "Locomotion", blendType = BlendTreeType.Simple1D, blendParameter = "Speed", useAutomaticThresholds = false };
            AssetDatabase.AddObjectToAsset(tree, c);
            var run = MoveSpeedMeters(new ControllerSpec { SpeedSourceId = "enemy.ash_hound", Hero = false });
            tree.AddChild(EchoesAnimationImport.Clip(EchoesAnimationImport.HoundIdle), 0f);
            tree.AddChild(EchoesAnimationImport.Clip(EchoesAnimationImport.HoundWalk), run * 0.45f);
            tree.AddChild(EchoesAnimationImport.Clip(EchoesAnimationImport.HoundRun), run);
            var loco = sm.AddState("Locomotion");
            loco.motion = tree;
            sm.defaultState = loco;
            var flee = sm.AddState("Flee");
            flee.motion = EchoesAnimationImport.Clip(EchoesAnimationImport.HoundFlee);
            var death = sm.AddState("Death");
            death.motion = EchoesAnimationImport.Clip(EchoesAnimationImport.HoundDeath);

            var toFlee = loco.AddTransition(flee);
            toFlee.AddCondition(AnimatorConditionMode.If, 0f, "IsFleeing");
            toFlee.hasExitTime = false;
            toFlee.duration = 0.1f;
            var fromFlee = flee.AddTransition(loco);
            fromFlee.AddCondition(AnimatorConditionMode.IfNot, 0f, "IsFleeing");
            fromFlee.hasExitTime = false;
            fromFlee.duration = 0.15f;
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

            c.AddLayer("Action");
            var layers = c.layers;
            layers[1].defaultWeight = 1f;
            c.layers = layers;
            var action = c.layers[1].stateMachine;
            var empty = action.AddState("Empty");
            action.defaultState = empty;
            var bite = action.AddState("Bite");
            bite.motion = EchoesAnimationImport.Clip(EchoesAnimationImport.HoundBite);
            bite.speedParameterActive = true;
            bite.speedParameter = "ActionSpeed";
            var back = bite.AddTransition(empty);
            back.hasExitTime = true;
            back.exitTime = 1f;
            back.hasFixedDuration = true;
            back.duration = ExitBlendSeconds;

            c.AddLayer("Hit");
            layers = c.layers;
            layers[2].defaultWeight = 1f;
            c.layers = layers;
            var hitMachine = c.layers[2].stateMachine;
            var hitEmpty = hitMachine.AddState("Empty");
            hitMachine.defaultState = hitEmpty;
            var hit = hitMachine.AddState("Hit");
            hit.motion = EchoesAnimationImport.Clip(EchoesAnimationImport.HoundHit);
            var hitBack = hit.AddTransition(hitEmpty);
            hitBack.hasExitTime = true;
            hitBack.exitTime = 1f;
            hitBack.hasFixedDuration = true;
            hitBack.duration = ExitBlendSeconds;
            EditorUtility.SetDirty(c);
            return c;
        }

        public static SkillPresentationSet BuildHoundSkillSet()
        {
            SandboxBuilder.EnsureDir(SkillSetDir);
            var set = SandboxBuilder.LoadOrCreate<SkillPresentationSet>($"{SkillSetDir}/{HoundSkillSetName}.asset");
            set.entries.Clear();
            var bite = EchoesAnimationImport.Spec(EchoesAnimationImport.HoundBite);
            // O core manda as fases (preparacao, impacto, recuperacao); a velocidade do clipe segue os tempos do core (ActionSpeed).
            set.entries.Add(new SkillPresentationEntry
            {
                skillId = HoundSkillId, animatorState = "Bite", clipSeconds = bite.Seconds,
                windupEnd = EchoesAnimationImport.HoundBiteWindupFrame / (float)bite.Frames,
                impactEnd = EchoesAnimationImport.HoundBiteImpactFrame / (float)bite.Frames,
                anchor = "Head",
            });
            set.dodgeState = "Dodge";
            EditorUtility.SetDirty(set);
            return set;
        }

        public static SkillPresentationSet BuildArcherSkillSet()
        {
            SandboxBuilder.EnsureDir(SkillSetDir);
            var set = SandboxBuilder.LoadOrCreate<SkillPresentationSet>($"{SkillSetDir}/{ArcherSkillSetName}.asset");
            set.entries.Clear();
            var shoot = EchoesAnimationImport.Spec("AN_GhostArcher_Shoot");
            // A preparacao termina no quadro do disparo (release, 20) e o impacto logo depois: o core dispara o projetil no fim da preparacao.
            set.entries.Add(new SkillPresentationEntry
            {
                skillId = ArcherSkillId, animatorState = "Shoot", clipSeconds = shoot.Seconds,
                windupEnd = EchoesAnimationImport.ShootReleaseFrame / (float)shoot.Frames,
                impactEnd = (EchoesAnimationImport.ShootReleaseFrame + 4) / (float)shoot.Frames,
                anchor = "Hips",
            });
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
                case "enemy.ghost_archer":
                    return $"{SkillSetDir}/{ArcherSkillSetName}.asset";
                case "enemy.ash_hound":
                case "enemy.swift_ash_hound":
                    return $"{SkillSetDir}/{HoundSkillSetName}.asset";
                default:
                    return null;
            }
        }

        public static string WarriorSkillSetPath => $"{SkillSetDir}/{Warrior.SkillSet}.asset";
        public static string ArcherHeroSkillSetPath => $"{SkillSetDir}/{HeroArcher.SkillSet}.asset";
        public static string MageHeroSkillSetPath => $"{SkillSetDir}/{HeroMage.SkillSet}.asset";
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

        /// <summary>Antecedencia (s) da pose de carga em relacao ao inicio do golpe rapido: a pose congela aqui e a preparacao do core (curta) cobre so o resto.</summary>
        public const float HoldLeadSeconds = 0.15f;

        /// <summary>
        /// Quadro "arma atras" do golpe carregado (parametro holdAt, normalizado): <see cref="HoldLeadSeconds"/> antes do fim da preparacao medida
        /// (limitado a metade dela). E nessa pose, ja encolhida mas ainda em movimento, que o clipe congela enquanto carrega e de onde o golpe solta;
        /// a preparacao curta do core (heavy_slash = 0,10 s) ainda mostra um trecho real do armar, sem parada seca.
        /// </summary>
        public static float FindHoldPose(GameObject instance, AnimationClip clip, float windupEnd)
        {
            if (clip.length < 0.1f) return windupEnd;
            var windupSeconds = windupEnd * clip.length;
            var hold = windupSeconds - Mathf.Min(HoldLeadSeconds, windupSeconds * 0.5f);
            return Mathf.Clamp(hold / clip.length, 0.02f, windupEnd);
        }
    }
}
