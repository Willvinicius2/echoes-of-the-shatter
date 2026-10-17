using System.Collections.Generic;
using Echoes.Presentation;
using UnityEditor;
using UnityEngine;

namespace Echoes.EditorTools
{
    /// <summary>Cria/atualiza um SO_WeaponOffset_&lt;Arma&gt; por arma em Assets/Data/Presentation/Weapons. Os valores padrao sao de apresentacao.</summary>
    public static class WeaponOffsetBuilder
    {
        public const string Dir = "Assets/Data/Presentation/Weapons";

        /// <summary>Pe a arma (autorada com o comprimento no eixo Y e a face no Z) em pe no eixo Z da mao (Rx 90) e depois gira essa pose em torno do eixo da mao (Rz): quem manda e a ordem Rx primeiro, Rz depois.</summary>
        static Vector3 Stand(float yawAroundHand) => (Quaternion.Euler(0f, 0f, yawAroundHand) * Quaternion.Euler(90f, 0f, 0f)).eulerAngles;

        // nome -> (posicao local, euler local). Ajustados por captura (armas_*.png). Martelo: identidade (ja alinhado).
        static readonly Dictionary<string, (Vector3 pos, Vector3 euler)> Defaults = new Dictionary<string, (Vector3, Vector3)>
        {
            { "WarriorHammer", (Vector3.zero, Vector3.zero) },
            { "GuardianHammer", (Vector3.zero, Vector3.zero) },
            { "WarriorShield", (Vector3.zero, Stand(180f)) },
            { "GuardianShield", (Vector3.zero, Stand(180f)) },
            { "Bow", (Vector3.zero, Stand(90f)) },
            { "Staff", (Vector3.zero, new Vector3(90f, 0f, 0f)) },
        };

        /// <summary>Retorna o asset da arma, criando com o padrao se nao existir (nunca sobrescreve valores ja ajustados).</summary>
        public static WeaponOffsetAsset Get(string weaponName)
        {
            string path = $"{Dir}/SO_WeaponOffset_{weaponName}.asset";
            var so = AssetDatabase.LoadAssetAtPath<WeaponOffsetAsset>(path);
            if (so != null) return so;
            if (!AssetDatabase.IsValidFolder(Dir))
            {
                if (!AssetDatabase.IsValidFolder("Assets/Data/Presentation")) AssetDatabase.CreateFolder("Assets/Data", "Presentation");
                AssetDatabase.CreateFolder("Assets/Data/Presentation", "Weapons");
            }
            so = ScriptableObject.CreateInstance<WeaponOffsetAsset>();
            so.weaponName = weaponName;
            if (Defaults.TryGetValue(weaponName, out var d)) { so.localPosition = d.pos; so.localEuler = d.euler; }
            AssetDatabase.CreateAsset(so, path);
            AssetDatabase.SaveAssets();
            return so;
        }

        public static IEnumerable<string> Names => Defaults.Keys;
    }
}
