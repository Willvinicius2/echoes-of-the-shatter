using UnityEngine;

namespace Echoes.Presentation
{
    /// <summary>
    /// Ponto de fogo do cenario (braseiro, vela, brilho de portao): so DADOS de apresentacao. Quem acende luz e chama e o <see cref="FirePool"/>, so para as
    /// fontes mais proximas do heroi; as demais ficam so com o brilho da emissao da textura (canal R da mascara).
    /// </summary>
    public sealed class FireSource : MonoBehaviour
    {
        public Color lightColor = new Color(1f, 0.55f, 0.2f);
        public float lightIntensity = 2f;
        public float lightRange = 9f;
        public bool flame = true;
        public float flameHeight = 1.45f;
        public float flameScale = 1f;

        public Vector3 FirePoint => transform.position + Vector3.up * flameHeight;
    }
}
