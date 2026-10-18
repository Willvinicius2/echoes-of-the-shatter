using System;
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
    }
}
