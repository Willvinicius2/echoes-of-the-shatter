using UnityEngine;

namespace Echoes.Presentation
{
    /// <summary>
    /// SO_WeaponOffset_&lt;Arma&gt;: offset de apresentacao da arma no socket da mao (posicao local em metros, rotacao local em graus Euler,
    /// escala uniforme). Corrige a diferenca entre os eixos do pivo do FBX da arma e os do osso da mao. Dado de apresentacao: NAO e
    /// balanceamento. Aplicado por <see cref="Apply"/> ao instanciar a arma no socket.
    /// </summary>
    [CreateAssetMenu(menuName = "Echoes/Weapon Offset", fileName = "SO_WeaponOffset")]
    public sealed class WeaponOffsetAsset : ScriptableObject
    {
        public string weaponName;
        public Vector3 localPosition;
        public Vector3 localEuler;
        public float uniformScale = 1f;

        public void Apply(Transform weapon)
        {
            weapon.localPosition = localPosition;
            weapon.localRotation = Quaternion.Euler(localEuler);
            weapon.localScale = Vector3.one * uniformScale;
        }
    }
}
