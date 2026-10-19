using Echoes.Presentation;
using UnityEditor;
using UnityEngine;

namespace Echoes.EditorTools
{
    /// <summary>Poe a HeroAura (anel + particulas, cor do heroi) nos prefabs P_Hero_*. Menu Echoes/Herois/Aura ou -executeMethod Echoes.EditorTools.HeroAuraSetup.Apply.</summary>
    public static class HeroAuraSetup
    {
        static readonly (string prefab, Color color)[] Heroes =
        {
            ("P_Hero_Warrior", new Color(1f, 0.30f, 0.20f)),
            ("P_Hero_Mage",    new Color(0.45f, 0.40f, 1f)),
            ("P_Hero_Archer",  new Color(0.35f, 1f, 0.55f)),
        };

        [MenuItem("Echoes/Herois/Aura")]
        public static void Apply()
        {
            var ring = AssetDatabase.LoadAssetAtPath<Material>("Assets/Art/VFX/Materials/M_VFX_AddRingSoft.mat");
            var mote = AssetDatabase.LoadAssetAtPath<Material>("Assets/Art/VFX/Materials/M_VFX_AddSoft.mat");
            foreach (var (name, color) in Heroes)
            {
                var path = $"Assets/Art/Prefabs/{name}.prefab";
                var root = PrefabUtility.LoadPrefabContents(path);
                var a = root.GetComponent<HeroAura>() ?? root.AddComponent<HeroAura>();
                a.Configure(color, ring, mote);
                PrefabUtility.SaveAsPrefabAsset(root, path);
                PrefabUtility.UnloadPrefabContents(root);
                Debug.Log($"[HeroAura] {name}");
            }
            AssetDatabase.SaveAssets();
        }
    }
}
