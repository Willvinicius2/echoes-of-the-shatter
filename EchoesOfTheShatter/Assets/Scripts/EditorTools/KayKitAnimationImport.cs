using System.Collections.Generic;
using System.Linq;
using UnityEditor;
using UnityEngine;

namespace Echoes.EditorTools
{
    /// <summary>
    /// Importação reproduzível das animações CC0 do KayKit (Assets/Art/Animations/ThirdParty/KayKit, ver README da pasta): só os clipes
    /// necessários, como Humanoid (retarget pelo avatar para o Rig_Humanoid_Chibi), sem root motion (rotação, altura e XZ gravadas na pose;
    /// altura pelos pés, então o pé fica no chão) e os laços marcados. Também aplica o Muscle setup do chibi (braços curtos) no avatar do rig.
    /// Menu: Echoes ▸ Importar animações KayKit. Idempotente.
    /// </summary>
    public static class KayKitAnimationImport
    {
        public const string Root = "Assets/Art/Animations/ThirdParty/KayKit";

        public readonly struct ClipSpec
        {
            public readonly string Take;
            public readonly bool Loop;

            public ClipSpec(string take, bool loop = false)
            {
                Take = take;
                Loop = loop;
            }
        }

        /// <summary>FBX → clipes necessários (nome do clipe = nome do take do KayKit, para rastrear).</summary>
        public static readonly Dictionary<string, ClipSpec[]> Files = new Dictionary<string, ClipSpec[]>
        {
            {
                Root + "/Medium/Rig_Medium_General.fbx", new[]
                {
                    new ClipSpec("Idle_A", true), new ClipSpec("Hit_A"), new ClipSpec("Hit_B"), new ClipSpec("Death_A"), new ClipSpec("Death_B"),
                }
            },
            { Root + "/Medium/Rig_Medium_MovementBasic.fbx", new[] { new ClipSpec("Walking_A", true), new ClipSpec("Running_A", true) } },
            { Root + "/Medium/Rig_Medium_MovementAdvanced.fbx", new[] { new ClipSpec("Dodge_Forward") } },
            {
                Root + "/Medium/Rig_Medium_CombatMelee.fbx", new[]
                {
                    new ClipSpec("Melee_1H_Attack_Slice_Horizontal"), new ClipSpec("Melee_1H_Attack_Chop"), new ClipSpec("Melee_1H_Attack_Stab"),
                    new ClipSpec("Melee_2H_Attack_Chop"), new ClipSpec("Melee_Block_Attack"),
                }
            },
            { Root + "/Large/Rig_Large_General.fbx", new[] { new ClipSpec("Idle_A", true), new ClipSpec("Hit_A"), new ClipSpec("Death_A") } },
            { Root + "/Large/Rig_Large_MovementBasic.fbx", new[] { new ClipSpec("Walking_A", true), new ClipSpec("Running_A", true) } },
            { Root + "/Large/Rig_Large_CombatMelee.fbx", new[] { new ClipSpec("Melee_2H_Slam"), new ClipSpec("Melee_Block_Attack") } },
            { Root + "/Large/Rig_Large_Simulation.fbx", new[] { new ClipSpec("Flexing") } },
        };

        /// <summary>
        /// Muscle setup do chibi (braços curtos): o stretch deixa a mão alcançar a pose do clipe de proporção humana sem a pose de braços curtos.
        /// Valores de arte (0 a 1), ajustados olhando as capturas; o pé no chão vem do "Based Upon: Feet" dos clipes.
        /// </summary>
        public const float ArmStretch = 0.5f;
        public const float LegStretch = 0.1f;

        [MenuItem("Echoes/Importar animações KayKit")]
        public static void Apply()
        {
            foreach (var pair in Files) ConfigureClips(pair.Key, pair.Value);
            ConfigureChibiMuscles();
        }

        public static AnimationClip FindClip(string fbxPath, string clipName)
        {
            return AssetDatabase.LoadAllAssetsAtPath(fbxPath).OfType<AnimationClip>().FirstOrDefault(c => c.name == clipName);
        }

        static void ConfigureClips(string path, ClipSpec[] specs)
        {
            var importer = AssetImporter.GetAtPath(path) as ModelImporter;
            if (importer == null)
            {
                Debug.LogWarning("[KayKitAnimationImport] FBX ausente: " + path);
                return;
            }
            var wanted = specs.Select(s => s.Take).ToList();
            var current = importer.clipAnimations;
            if (current != null && current.Length == wanted.Count && current.All(c => wanted.Contains(c.name)) && current.All(c => c.lockRootHeightY && c.heightFromFeet)) return;

            var defaults = importer.defaultClipAnimations;
            var clips = new List<ModelImporterClipAnimation>();
            foreach (var spec in specs)
            {
                var source = defaults.FirstOrDefault(d => d.takeName == spec.Take);
                if (source == null)
                {
                    Debug.LogWarning($"[KayKitAnimationImport] Take '{spec.Take}' nao encontrado em {path}");
                    continue;
                }
                source.name = spec.Take;
                source.loopTime = spec.Loop;
                source.loopPose = spec.Loop;
                // Sem root motion: a logica move o personagem. Rotacao, altura (pelos pes) e XZ gravadas na pose.
                source.lockRootRotation = true;
                source.keepOriginalOrientation = false;
                source.lockRootHeightY = true;
                source.keepOriginalPositionY = false;
                source.heightFromFeet = true;
                source.lockRootPositionXZ = true;
                source.keepOriginalPositionXZ = false;
                clips.Add(source);
            }
            importer.clipAnimations = clips.ToArray();
            importer.SaveAndReimport();
        }

        static void ConfigureChibiMuscles()
        {
            var importer = AssetImporter.GetAtPath(CharacterAssetPostprocessor.RigPath) as ModelImporter;
            if (importer == null) return;
            var description = importer.humanDescription;
            if (description.human == null || description.human.Length == 0) return; // ainda sem mapeamento: reimporta antes
            if (Mathf.Approximately(description.armStretch, ArmStretch) && Mathf.Approximately(description.legStretch, LegStretch)) return;
            description.armStretch = ArmStretch;
            description.legStretch = LegStretch;
            importer.humanDescription = description;
            importer.SaveAndReimport();
        }
    }
}
