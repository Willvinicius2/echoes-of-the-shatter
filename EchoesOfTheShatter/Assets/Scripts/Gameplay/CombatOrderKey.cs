using System.Text;
using UnityEngine;

namespace Echoes.Gameplay
{
    /// <summary>
    /// Chave de ordem estável de um objeto da cena para o <see cref="CombatSystem"/>: o caminho de
    /// índices na hierarquia ("0002/0000/0003"). A ordem dos Start não é garantida pela Unity; esta é.
    /// </summary>
    public static class CombatOrderKey
    {
        public static string Of(Transform transform)
        {
            if (transform == null) return null;
            var sb = new StringBuilder(32);
            Append(sb, transform);
            return sb.ToString();
        }

        static void Append(StringBuilder sb, Transform t)
        {
            if (t.parent != null)
            {
                Append(sb, t.parent);
                sb.Append('/');
            }
            sb.Append(t.GetSiblingIndex().ToString("D4", System.Globalization.CultureInfo.InvariantCulture));
        }
    }
}
