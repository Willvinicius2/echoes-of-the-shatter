using System.Linq;
using UnityEditor;
using UnityEngine;

namespace Echoes.EditorTools
{
    /// <summary>
    /// Importação dos golpes feitos no Blender por script (Assets/Art/Animations/Echoes; fonte: animacoes/blender, quadros, laço e eventos em
    /// _clips_*.json): um clipe por FBX só de armature. Stun (Rig_Humanoid_Chibi, Humanoid), Guardião (esqueleto do m08, avatar do Guardião,
    /// Humanoid) e Arqueiro Espectral (esqueleto do m07, Generic). Sem root motion; os eventos de clipe chamam OnClipEvent(nome) no
    /// AnimationEventRelay do prefab. Menu: Echoes, Importar golpes do Blender. Idempotente.
    /// </summary>
    public static class EchoesAnimationImport
    {
        public const string Root = "Assets/Art/Animations/Echoes";
        public const float Fps = 30f;
        public const string EventFunction = "OnClipEvent";

        public enum Kind { SharedHumanoid, GuardianHumanoid, ArcherGeneric, HoundGeneric }

        public static bool IsGeneric(Kind kind) => kind == Kind.ArcherGeneric || kind == Kind.HoundGeneric;

        public readonly struct ClipSpec
        {
            public readonly string Name;
            public readonly Kind Kind;
            public readonly int Frames;
            public readonly bool Loop;
            public readonly (string name, int frame)[] Events;

            public ClipSpec(string name, Kind kind, int frames, bool loop, params (string, int)[] events)
            {
                Name = name;
                Kind = kind;
                Frames = frames;
                Loop = loop;
                Events = events;
            }

            public string Path => $"{Root}/{Name}.fbx";
            public float Seconds => Frames / Fps;
        }

        public const string StunName = "AN_Shared_Stun";
        public const string RoarName = "AN_Guardian_Roar";
        public const string ChargeWindupName = "AN_Guardian_ShieldCharge_Windup";
        public const string ChargeRunName = "AN_Guardian_ShieldCharge_Run";
        public const string ChargeRecoverName = "AN_Guardian_ShieldCharge_Recover";
        public const int ShootReleaseFrame = 20;
        public const string HoundIdle = "AN_AshHound_Idle", HoundWalk = "AN_AshHound_Walk", HoundRun = "AN_AshHound_Run", HoundBite = "AN_AshHound_Bite";
        public const string HoundHit = "AN_AshHound_Hit", HoundFlee = "AN_AshHound_Flee", HoundDeath = "AN_AshHound_Death";
        public const int HoundBiteWindupFrame = 9, HoundBiteImpactFrame = 12;

        /// <summary>Quadros, laço e eventos iguais aos de _clips_*.json.</summary>
        public static readonly ClipSpec[] Clips =
        {
            new ClipSpec(StunName, Kind.SharedHumanoid, 24, true),
            new ClipSpec(RoarName, Kind.GuardianHumanoid, 60, false, ("summon_marks", 30), ("slam", 48)),
            new ClipSpec(ChargeWindupName, Kind.GuardianHumanoid, 27, false),
            new ClipSpec(ChargeRunName, Kind.GuardianHumanoid, 18, true),
            new ClipSpec(ChargeRecoverName, Kind.GuardianHumanoid, 30, false),
            new ClipSpec("AN_GhostArcher_Idle", Kind.ArcherGeneric, 60, true),
            new ClipSpec("AN_GhostArcher_Glide", Kind.ArcherGeneric, 36, true),
            new ClipSpec("AN_GhostArcher_Shoot", Kind.ArcherGeneric, 44, false, ("draw_start", 5), ("aim_end", 19), ("release", ShootReleaseFrame)),
            new ClipSpec("AN_GhostArcher_Hit", Kind.ArcherGeneric, 12, false),
            new ClipSpec("AN_GhostArcher_Death", Kind.ArcherGeneric, 36, false),
            // Cao de Cinza (quadrupede, Generic): a mordida tem os eventos do clipe (preparacao ate o quadro 9, impacto no 12, fim da recuperacao no 24).
            new ClipSpec(HoundIdle, Kind.HoundGeneric, 60, true),
            new ClipSpec(HoundWalk, Kind.HoundGeneric, 32, true),
            new ClipSpec(HoundRun, Kind.HoundGeneric, 20, true),
            new ClipSpec(HoundBite, Kind.HoundGeneric, 24, false, ("windup_end", 9), ("impact", 12), ("recovery_end", 24)),
            new ClipSpec(HoundHit, Kind.HoundGeneric, 12, false),
            new ClipSpec(HoundFlee, Kind.HoundGeneric, 24, true),
            new ClipSpec(HoundDeath, Kind.HoundGeneric, 36, false),
        };

        public static ClipSpec Spec(string name) => Clips.First(c => c.Name == name);

        public static string PathOf(string name) => Spec(name).Path;

        public static AnimationClip Clip(string name) => KayKitAnimationImport.FindClip(PathOf(name), name);

        [MenuItem("Echoes/Importar golpes do Blender")]
        public static void Apply()
        {
            foreach (var spec in Clips) ConfigureClip(spec);
        }

        static bool IsConfigured(ModelImporter importer, ClipSpec spec)
        {
            var current = importer.clipAnimations;
            if (current == null || current.Length != 1 || current[0].name != spec.Name || current[0].loopTime != spec.Loop) return false;
            if (current[0].events == null || current[0].events.Length != spec.Events.Length) return false;
            if (!IsGeneric(spec.Kind) && !(current[0].lockRootHeightY && current[0].heightFromFeet)) return false;
            return true;
        }

        static void ConfigureClip(ClipSpec spec)
        {
            var importer = AssetImporter.GetAtPath(spec.Path) as ModelImporter;
            if (importer == null)
            {
                Debug.LogWarning("[EchoesAnimationImport] FBX ausente: " + spec.Path);
                return;
            }
            if (IsConfigured(importer, spec) && importer.animationCompression == ModelImporterAnimationCompression.Off) return;

            // O take da animação (o Blender pode exportar também um take vazio): o mais longo.
            var takes = importer.defaultClipAnimations;
            if (takes.Length == 0)
            {
                Debug.LogWarning("[EchoesAnimationImport] Sem take em " + spec.Path + " (avatar nao validou?)");
                return;
            }
            var take = takes.OrderByDescending(c => c.lastFrame - c.firstFrame).First();
            take.name = spec.Name;
            take.loopTime = spec.Loop;
            take.loopPose = spec.Loop;
            take.lockRootRotation = true;
            take.keepOriginalOrientation = true;
            take.lockRootHeightY = true;
            take.keepOriginalPositionY = false;
            take.heightFromFeet = !IsGeneric(spec.Kind); // o Espectro flutua (sem pés)
            take.lockRootPositionXZ = true;
            take.keepOriginalPositionXZ = false;
            var length = Mathf.Max(1f, take.lastFrame - take.firstFrame);
            // Eventos de clipe no importer: tempo normalizado (0 a 1) pelo comprimento do clipe.
            take.events = spec.Events.Select(e => new AnimationEvent
            {
                functionName = EventFunction,
                stringParameter = e.name,
                time = e.frame / length,
            }).ToArray();
            importer.clipAnimations = new[] { take };
            importer.animationCompression = ModelImporterAnimationCompression.Off; // sem Keyframe Reduction: o erro alto dava tremor de pose
            importer.SaveAndReimport();
        }
    }
}
