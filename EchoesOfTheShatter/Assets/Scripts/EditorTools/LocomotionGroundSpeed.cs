using System.Collections.Generic;
using System.IO;
using UnityEditor;
using UnityEngine;

namespace Echoes.EditorTools
{
    /// <summary>
    /// Mede a velocidade de solo (m/s) dos clipes Walking_A e Running_A no rig de cada personagem, amostrando o pé de apoio (o mais baixo):
    /// o pé de apoio anda para trás na velocidade em que o personagem deveria andar para frente. O <see cref="AnimatorControllerBuilder"/> usa
    /// o resultado como timeScale dos filhos da árvore Locomotion (velocidade do jogo ÷ velocidade do clipe), para o pé não deslizar.
    /// É medida de arte (não é balanceamento); gravada em Assets/Data/Presentation/LocomotionGroundSpeeds.json. Menu: Echoes ▸ Medir velocidade de solo.
    /// </summary>
    public static class LocomotionGroundSpeed
    {
        public const string JsonPath = "Assets/Data/Presentation/LocomotionGroundSpeeds.json";

        /// <summary>Limites do ajuste de reprodução (timeScale) para a pose não ficar apressada nem arrastada.</summary>
        public const float MinScale = 0.75f, MaxScale = 1.35f;

        [System.Serializable]
        public sealed class Entry
        {
            public string controller;
            public float walk;
            public float run;
        }

        [System.Serializable]
        sealed class Table
        {
            public List<Entry> entries = new List<Entry>();
        }

        static readonly (string controller, string prefab, bool large)[] Targets =
        {
            ("AC_Warrior", "Assets/Art/Prefabs/P_Hero_Warrior.prefab", false),
            ("AC_EnemyHumanoid", "Assets/Art/Prefabs/P_Enemy_HollowSentinel.prefab", false),
            ("AC_Boss", "Assets/Art/Prefabs/P_Boss_CryptGuardian.prefab", true),
        };

        public static float Clamp(float scale) => Mathf.Clamp(scale, MinScale, MaxScale);

        /// <summary>Escala de reprodução = velocidade do jogo ÷ velocidade de solo do clipe, nos limites 0,75 a 1,35. Sem medida (≤ 0), 1.</summary>
        public static float PlaybackScale(float gameSpeed, float clipGroundSpeed)
        {
            if (clipGroundSpeed <= 0.01f || gameSpeed <= 0f) return 1f;
            return Clamp(gameSpeed / clipGroundSpeed);
        }

        public static Entry Load(string controller)
        {
            var full = Path.GetFullPath(Path.Combine(Application.dataPath, "../" + JsonPath));
            if (!File.Exists(full)) return null;
            var table = JsonUtility.FromJson<Table>(File.ReadAllText(full));
            return table?.entries?.Find(e => e.controller == controller);
        }

        [MenuItem("Echoes/Medir velocidade de solo da locomoção")]
        public static void MeasureAll()
        {
            var table = new Table();
            foreach (var target in Targets)
            {
                var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(target.prefab);
                if (prefab == null) { Debug.LogWarning("[GroundSpeed] prefab ausente: " + target.prefab); continue; }
                var group = target.large ? "Large" : "Medium";
                var fbx = $"{KayKitAnimationImport.Root}/{group}/Rig_{group}_MovementBasic.fbx";
                var walk = KayKitAnimationImport.FindClip(fbx, "Walking_A");
                var run = KayKitAnimationImport.FindClip(fbx, "Running_A");
                var instance = (GameObject)PrefabUtility.InstantiatePrefab(prefab);
                try
                {
                    var animator = instance.GetComponentInChildren<Animator>();
                    var entry = new Entry
                    {
                        controller = target.controller,
                        walk = Measure(instance, animator, walk),
                        run = Measure(instance, animator, run),
                    };
                    Debug.Log($"[GroundSpeed] {target.controller}: walk {entry.walk:F3} m/s, run {entry.run:F3} m/s");
                    table.entries.Add(entry);
                }
                finally
                {
                    Object.DestroyImmediate(instance);
                }
            }
            var full = Path.GetFullPath(Path.Combine(Application.dataPath, "../" + JsonPath));
            Directory.CreateDirectory(Path.GetDirectoryName(full));
            File.WriteAllText(full, JsonUtility.ToJson(table, true));
            AssetDatabase.ImportAsset(JsonPath);
        }

        /// <summary>Velocidade média do pé de apoio (para trás, em m/s) ao longo do laço do clipe.</summary>
        static float Measure(GameObject root, Animator animator, AnimationClip clip)
        {
            if (clip == null || animator == null) return 0f;
            var left = animator.GetBoneTransform(HumanBodyBones.LeftFoot);
            var right = animator.GetBoneTransform(HumanBodyBones.RightFoot);
            if (left == null || right == null) return 0f;
            var forward = root.transform.forward;
            const int steps = 120;
            var dt = clip.length / steps;
            var sum = 0f;
            var count = 0;
            float Fwd(Transform t) => Vector3.Dot(t.position, forward);

            clip.SampleAnimation(animator.gameObject, 0f);
            var prevL = Fwd(left);
            var prevR = Fwd(right);
            var prevLeftLower = left.position.y < right.position.y;
            for (var i = 1; i <= steps; i++)
            {
                clip.SampleAnimation(animator.gameObject, i * dt);
                var l = Fwd(left);
                var r = Fwd(right);
                var leftLower = left.position.y < right.position.y;
                if (leftLower == prevLeftLower)
                {
                    var v = -((leftLower ? l - prevL : r - prevR) / dt);
                    if (v > 0f) { sum += v; count++; }
                }
                prevL = l;
                prevR = r;
                prevLeftLower = leftLower;
            }
            return count > 0 ? sum / count : 0f;
        }
    }
}
