using System;
using System.Linq;
using UnityEditor;
using UnityEngine;

namespace Echoes.EditorTools
{
    /// <summary>
    /// Passos em lote para o polimento de animação (batchmode, uma Unity só): <c>Prepare</c> importa os clipes, monta prefabs e controllers, mede a velocidade de solo
    /// (inclui o Arqueiro e o Mago) e monta de novo para a escala do pé entrar nos controllers. <c>-executeMethod Echoes.EditorTools.DevPipeline.Prepare</c>.
    /// </summary>
    public static class DevPipeline
    {
        public static void Prepare()
        {
            try
            {
                CharacterPrefabBuilder.BuildAll();
                LocomotionGroundSpeed.MeasureAll();
                CharacterPrefabBuilder.BuildAll();
                AssetDatabase.SaveAssets();
                Debug.Log("[DevPipeline] Prepare OK");
                EditorApplication.Exit(0);
            }
            catch (Exception e)
            {
                Debug.LogError("[DevPipeline] Prepare falhou: " + e);
                EditorApplication.Exit(1);
            }
        }

        /// <summary>
        /// Diagnóstico (batchmode): duração de cada clipe dos controllers e a trajetória da mão da arma do golpe forte do Guerreiro
        /// (frente e altura em relação ao corpo, velocidade), para ajustar o holdAt e as transições da camada Upper.
        /// <c>-executeMethod Echoes.EditorTools.DevPipeline.Diagnose</c>.
        /// </summary>
        public static void Diagnose()
        {
            try
            {
                foreach (var spec in AnimatorControllerBuilder.All)
                {
                    foreach (var action in spec.Actions) LogClip(spec.Name + "/" + action.State, action.Fbx, action.Clip);
                    foreach (var upper in spec.Upper) LogClip(spec.Name + "/Upper/" + upper.State, upper.Fbx, upper.Clip);
                }
                var prefab = AssetDatabase.LoadAssetAtPath<GameObject>("Assets/Art/Prefabs/P_Hero_Warrior.prefab");
                var instance = (GameObject)PrefabUtility.InstantiatePrefab(prefab);
                try
                {
                    var heavy = AnimatorControllerBuilder.Warrior.Actions.Find(a => a.State == "HeavyRelease");
                    var clip = KayKitAnimationImport.FindClip(heavy.Fbx, heavy.Clip);
                    var hand = CharacterPrefabBuilder.FindDeep(instance.transform, "RightHand");
                    var sb = new System.Text.StringBuilder();
                    sb.AppendLine($"[Diag] {heavy.Clip}: {clip.length:F3} s; quadro: t, normalizado, frente(m), altura(m), velocidade da mao (m/s)");
                    var previous = Vector3.zero;
                    const float fps = 30f;
                    for (var i = 0; i <= Mathf.CeilToInt(clip.length * fps); i++)
                    {
                        var t = Mathf.Min(clip.length, i / fps);
                        clip.SampleAnimation(instance, t);
                        var local = instance.transform.InverseTransformPoint(hand.position);
                        sb.AppendLine($"[Diag] {t:F3} {t / clip.length:F3} frente {local.z:F3} altura {local.y:F3} lado {local.x:F3} vel {(i > 0 ? (hand.position - previous).magnitude * fps : 0f):F2}");
                        previous = hand.position;
                    }
                    Debug.Log(sb.ToString());
                    var medium = KayKitAnimationImport.Root + "/Medium/";
                    DiagnosePose(instance, "guarda", medium + "Rig_Medium_CombatMelee.fbx", "Melee_Block", medium + "Rig_Medium_CombatMelee.fbx", "Melee_Blocking", 0f);
                    DiagnosePose(instance, "guarda meio", medium + "Rig_Medium_CombatMelee.fbx", "Melee_Block", medium + "Rig_Medium_CombatMelee.fbx", "Melee_Blocking", 0.5f);
                    DiagnosePose(instance, "mago guarda", medium + "Rig_Medium_CombatRanged.fbx", "Ranged_Magic_Raise", null, null, 0f);
                    DiagnosePose(instance, "mago carga", medium + "Rig_Medium_CombatRanged.fbx", "Ranged_Magic_Spellcasting_Long", null, null, 0f);
                    DiagnosePose(instance, "arco puxar", medium + "Rig_Medium_CombatRanged.fbx", "Ranged_Bow_Draw", medium + "Rig_Medium_CombatRanged.fbx", "Ranged_Bow_Aiming_Idle", 0f);
                    DiagnosePose(instance, "arco soltar", medium + "Rig_Medium_CombatRanged.fbx", "Ranged_Bow_Release", null, null, 0f);
                    DiagnosePose(instance, "forte golpe 2h", medium + "Rig_Medium_CombatMelee.fbx", "Melee_2H_Attack_Chop", null, null, 0f);
                }
                finally
                {
                    UnityEngine.Object.DestroyImmediate(instance);
                }
                EditorApplication.Exit(0);
            }
            catch (Exception e)
            {
                Debug.LogError("[DevPipeline] Diagnose falhou: " + e);
                EditorApplication.Exit(1);
            }
        }

        static readonly HumanBodyBones[] PoseBones =
        {
            HumanBodyBones.RightHand, HumanBodyBones.LeftHand, HumanBodyBones.RightLowerArm, HumanBodyBones.LeftLowerArm,
            HumanBodyBones.RightUpperArm, HumanBodyBones.LeftUpperArm, HumanBodyBones.Head, HumanBodyBones.Chest,
        };

        static Vector3[] SamplePose(GameObject instance, Animator animator, AnimationClip clip, float time)
        {
            clip.SampleAnimation(instance, time);
            var pose = new Vector3[PoseBones.Length];
            for (var i = 0; i < pose.Length; i++)
            {
                var bone = animator.GetBoneTransform(PoseBones[i]);
                pose[i] = bone != null ? instance.transform.InverseTransformPoint(bone.position) : Vector3.zero;
            }
            return pose;
        }

        static float PoseDistance(Vector3[] a, Vector3[] b)
        {
            var sum = 0f;
            for (var i = 0; i < a.Length; i++) sum += (a[i] - b[i]).magnitude;
            return sum;
        }

        /// <summary>Distancia de cada quadro de <paramref name="clipName"/> a uma pose alvo e velocidade da pose, para achar onde o clipe "chega" (ex.: Melee_Block ate Melee_Blocking).</summary>
        static void DiagnosePose(GameObject instance, string label, string fbx, string clipName, string targetFbx, string targetClip, float targetTime)
        {
            var animator = instance.GetComponentInChildren<Animator>();
            var clip = KayKitAnimationImport.FindClip(fbx, clipName);
            var target = targetClip != null ? SamplePose(instance, animator, KayKitAnimationImport.FindClip(targetFbx, targetClip), targetTime) : null;
            var sb = new System.Text.StringBuilder();
            sb.AppendLine($"[Diag] pose {label}: {clipName} {clip.length:F3} s" + (target != null ? $" ate {targetClip}@{targetTime:F2}" : " (velocidade da pose)"));
            const float fps = 30f;
            Vector3[] previous = null;
            for (var i = 0; i <= Mathf.CeilToInt(clip.length * fps); i++)
            {
                var t = Mathf.Min(clip.length, i / fps);
                var pose = SamplePose(instance, animator, clip, t);
                var speed = previous != null ? PoseDistance(pose, previous) * fps : 0f;
                sb.AppendLine($"[Diag] {t:F3} {t / clip.length:F3} dist {(target != null ? PoseDistance(pose, target) : 0f):F3} vel {speed:F2}");
                previous = pose;
            }
            Debug.Log(sb.ToString());
        }

        static void LogClip(string label, string fbx, string clipName)
        {
            var clip = KayKitAnimationImport.FindClip(fbx, clipName);
            if (clip == null) clip = AssetDatabase.LoadAllAssetsAtPath(fbx).OfType<AnimationClip>().FirstOrDefault(c => c.name == clipName);
            Debug.Log($"[Diag] clipe {label}: {clipName} = {(clip != null ? clip.length.ToString("F3") : "AUSENTE")} s");
        }
    }
}
