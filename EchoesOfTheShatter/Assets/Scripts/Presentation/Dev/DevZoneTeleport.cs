using UnityEngine;
using UnityEngine.InputSystem;

namespace Echoes.Presentation
{
    /// <summary>
    /// SÓ DESENVOLVIMENTO: F5 leva o herói à zona A, F6 à zona B da cena de escala. Desliga e religa o
    /// CharacterController (senão ele desfaz a mudança de posição), corta a suavização da câmera e move o
    /// checkpoint junto, para morrer na zona B voltar à zona B.
    /// </summary>
    [DisallowMultipleComponent]
    public sealed class DevZoneTeleport : MonoBehaviour
    {
        [SerializeField] Transform hero;
        [SerializeField] FollowCamera followCamera;
        [Tooltip("Checkpoint do HeroController (movido junto com o herói). Opcional.")]
        [SerializeField] Transform checkpoint;
        [SerializeField] Transform zoneA;
        [SerializeField] Transform zoneB;
        [Tooltip("Deslocamento do checkpoint em relação ao ponto de chegada.")]
        [SerializeField] Vector3 checkpointOffset = new Vector3(3f, 0f, 0f);

        void Update()
        {
            var keyboard = Keyboard.current;
            if (keyboard == null) return;
            if (keyboard.f5Key.wasPressedThisFrame) TeleportTo(zoneA);
            else if (keyboard.f6Key.wasPressedThisFrame) TeleportTo(zoneB);
        }

        public void TeleportTo(Transform zone)
        {
            if (zone == null || hero == null) return;
            var controller = hero.GetComponent<CharacterController>();
            if (controller != null) controller.enabled = false;
            hero.SetPositionAndRotation(zone.position, zone.rotation);
            if (controller != null) controller.enabled = true;
            if (checkpoint != null) checkpoint.position = zone.position + checkpointOffset;
            if (followCamera != null) followCamera.SetTarget(hero, true);
        }
    }
}
