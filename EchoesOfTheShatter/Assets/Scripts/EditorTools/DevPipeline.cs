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
        /// <summary>
        /// Fechamento da Cripta: reimporta a arte, monta os herois modulares (inclui o conjunto Raro), os prefabs e as tres cenas (tela inicial,
        /// Refugio e Cripta). <c>-executeMethod Echoes.EditorTools.DevPipeline.PrepareMapa</c>.
        /// </summary>
        public static void PrepareMapa()
        {
            try
            {
                AssetDatabase.Refresh();
                HeroModularBuilder.BuildAll();
                CharacterPrefabBuilder.BuildAll();
                LocomotionGroundSpeed.MeasureAll();     // a escala do pe entra nos controllers (como o Prepare)
                CharacterPrefabBuilder.BuildAll();
                MenuBuilder.BuildScene();
                RefugioBuilder.BuildScene();
                CriptaBuilder.BuildScene();
                AssetDatabase.SaveAssets();
                Debug.Log("[DevPipeline] PrepareMapa OK");
                EditorApplication.Exit(0);
            }
            catch (Exception e)
            {
                Debug.LogError("[DevPipeline] PrepareMapa falhou: " + e);
                EditorApplication.Exit(1);
            }
        }

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
