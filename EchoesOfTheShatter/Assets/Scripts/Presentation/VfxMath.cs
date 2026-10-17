using UnityEngine;

namespace Echoes.Presentation
{
    /// <summary>Contas puras dos VFX (testáveis sem cena): a mistura da saída do projétil e a escala pelo raio real da habilidade.</summary>
    public static class VfxMath
    {
        /// <summary>
        /// Peso (0 a 1) da trajetória lógica sobre o deslocamento de saída da mão: 0 no lançamento, 1 depois de <paramref name="blendMeters"/> de voo
        /// (smoothstep, sem quina). Sem distância de mistura o visual já nasce na trajetória.
        /// </summary>
        public static float LaunchBlend(float traveledMeters, float blendMeters)
        {
            if (blendMeters <= 0.01f) return 1f;
            var t = Mathf.Clamp01(traveledMeters / blendMeters);
            return t * t * (3f - 2f * t);
        }

        /// <summary>Escala do efeito: <paramref name="baseScale"/> vezes (raio da habilidade / raio com que o prefab foi feito); sem raio, só a escala base.</summary>
        public static float RadiusScale(float skillRadiusMeters, float authoredRadiusMeters, float baseScale)
        {
            if (authoredRadiusMeters <= 0f || skillRadiusMeters <= 0f) return baseScale;
            return baseScale * skillRadiusMeters / authoredRadiusMeters;
        }
    }
}
