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

        /// <summary>
        /// Limite próprio da corrida (a caminhada segue em <see cref="MaxScale"/>): o herói corre bem mais rápido do que o clipe cobre, e o limite
        /// de 1,35 deixava o pé deslizar. Padrão 2,2 (corrida A aprovada na rev3: 4,5 m/s com o clipe de 2,057 m/s fecha em 2,19x e o pé não escorrega).
        /// Arte, não balanceamento. ECHOES_RUN_MAX_SCALE só sobrescreve ao montar para comparação em vídeo; sem a variável vale o padrão.
        /// </summary>
        public const float DefaultRunMaxScale = 2.2f;

        public static float RunMaxScale
        {
            get
            {
                var env = System.Environment.GetEnvironmentVariable("ECHOES_RUN_MAX_SCALE");
                return !string.IsNullOrEmpty(env) && float.TryParse(env, System.Globalization.NumberStyles.Float, System.Globalization.CultureInfo.InvariantCulture, out var value) && value >= MinScale
                    ? value
                    : DefaultRunMaxScale;
            }
        }

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

        // Controller, prefab e os clipes de caminhada e corrida que a árvore Locomotion usa (os do ControllerSpec).
        static (string controller, string prefab, AnimatorControllerBuilder.ControllerSpec spec)[] Targets => new[]
        {
            ("AC_Warrior", "Assets/Art/Prefabs/P_Hero_Warrior.prefab", AnimatorControllerBuilder.Warrior),
            ("AC_Archer", "Assets/Art/Prefabs/P_Hero_Archer.prefab", AnimatorControllerBuilder.HeroArcher),
            ("AC_Mage", "Assets/Art/Prefabs/P_Hero_Mage.prefab", AnimatorControllerBuilder.HeroMage),
            ("AC_EnemyHumanoid", "Assets/Art/Prefabs/P_Enemy_HollowSentinel.prefab", AnimatorControllerBuilder.EnemyHumanoid),
            ("AC_Boss", "Assets/Art/Prefabs/P_Boss_CryptGuardian.prefab", AnimatorControllerBuilder.Boss),
        };

        public static float Clamp(float scale, float max = MaxScale) => Mathf.Clamp(scale, MinScale, max);

        /// <summary>Escala de reprodução = velocidade do jogo ÷ velocidade de solo do clipe, entre 0,75 e <paramref name="max"/>. Sem medida (≤ 0), 1.</summary>
        public static float PlaybackScale(float gameSpeed, float clipGroundSpeed, float max = MaxScale)
        {
            if (clipGroundSpeed <= 0.01f || gameSpeed <= 0f) return 1f;
            return Clamp(gameSpeed / clipGroundSpeed, max);
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
                var group = target.spec.Rig;
                var fbx = $"{KayKitAnimationImport.Root}/{group}/Rig_{group}_MovementBasic.fbx";
                var walk = KayKitAnimationImport.FindClip(fbx, target.spec.WalkClip);
                var run = KayKitAnimationImport.FindClip(target.spec.RunFbx ?? fbx, target.spec.RunClip);
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
            MeasureHound(table);
            var full = Path.GetFullPath(Path.Combine(Application.dataPath, "../" + JsonPath));
            Directory.CreateDirectory(Path.GetDirectoryName(full));
            File.WriteAllText(full, JsonUtility.ToJson(table, true));
            AssetDatabase.ImportAsset(JsonPath);
        }

        /// <summary>Cão de Cinza (Generic, 4 patas): velocidade de solo da pata de apoio (a mais baixa) nos laços de Walk e Run.</summary>
        static void MeasureHound(Table table)
        {
            var prefab = AssetDatabase.LoadAssetAtPath<GameObject>("Assets/Art/Prefabs/P_Enemy_AshHound.prefab");
            if (prefab == null) { Debug.LogWarning("[GroundSpeed] P_Enemy_AshHound ausente"); return; }
            var instance = (GameObject)PrefabUtility.InstantiatePrefab(prefab);
            try
            {
                var paws = new List<Transform>();
                foreach (var t in instance.GetComponentsInChildren<Transform>()) if (t.name.EndsWith("Paw")) paws.Add(t);
                if (paws.Count < 4) { Debug.LogWarning("[GroundSpeed] Cao: patas nao encontradas (" + paws.Count + ")"); return; }
                var animator = instance.GetComponentInChildren<Animator>();
                var entry = new Entry
                {
                    controller = AnimatorControllerBuilder.HoundControllerName,
                    walk = MeasureFeet(instance, animator, EchoesAnimationImport.Clip(EchoesAnimationImport.HoundWalk), paws),
                    run = MeasureFeet(instance, animator, EchoesAnimationImport.Clip(EchoesAnimationImport.HoundRun), paws),
                };
                Debug.Log($"[GroundSpeed] {entry.controller}: walk {entry.walk:F3} m/s, run {entry.run:F3} m/s");
                table.entries.Add(entry);
            }
            finally
            {
                Object.DestroyImmediate(instance);
            }
        }

        // Patas em apoio = as que estao a menos de ContactHeight da mais baixa nos dois passos seguidos; a velocidade e a media, para tras, dessas patas.
        const float ContactHeight = 0.03f;

        static float MeasureFeet(GameObject root, Animator animator, AnimationClip clip, List<Transform> feet)
        {
            if (clip == null || animator == null) return 0f;
            var forward = root.transform.forward;
            const int steps = 120;
            var dt = clip.length / steps;
            var sum = 0f;
            var count = 0;
            var prevPos = new float[feet.Count];
            var prevContact = new bool[feet.Count];
            void Sample(float[] positions, bool[] contact)
            {
                var lowest = float.MaxValue;
                foreach (var foot in feet) lowest = Mathf.Min(lowest, foot.position.y);
                for (var i = 0; i < feet.Count; i++)
                {
                    positions[i] = Vector3.Dot(feet[i].position, forward);
                    contact[i] = feet[i].position.y < lowest + ContactHeight;
                }
            }
            clip.SampleAnimation(animator.gameObject, 0f);
            Sample(prevPos, prevContact);
            var pos = new float[feet.Count];
            var contactNow = new bool[feet.Count];
            for (var step = 1; step <= steps; step++)
            {
                clip.SampleAnimation(animator.gameObject, step * dt);
                Sample(pos, contactNow);
                for (var i = 0; i < feet.Count; i++)
                {
                    if (!(prevContact[i] && contactNow[i])) continue;
                    var v = -(pos[i] - prevPos[i]) / dt;
                    if (v > 0f)
                    {
                        sum += v;
                        count++;
                    }
                }
                System.Array.Copy(pos, prevPos, pos.Length);
                System.Array.Copy(contactNow, prevContact, contactNow.Length);
            }
            return count > 0 ? sum / count : 0f;
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
