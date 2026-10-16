using UnityEngine;
using UnityEngine.AI;

namespace Echoes.Gameplay
{
    /// <summary>
    /// Portão da Cripta (atalho A, porta da arena): colisor que bloqueia o herói e obstáculo que corta o NavMesh enquanto fechado.
    /// Aberto = sem colisor, sem malha, sem obstáculo.
    /// </summary>
    public sealed class GateBarrier : MonoBehaviour
    {
        [SerializeField] Collider blocker;
        [SerializeField] Renderer[] visuals;
        [SerializeField] NavMeshObstacle obstacle;
        [SerializeField] bool startClosed;

        public bool IsClosed { get; private set; }

        void Awake()
        {
            Set(startClosed);
        }

        public void Open() => Set(false);

        public void Close() => Set(true);

        void Set(bool closed)
        {
            IsClosed = closed;
            if (blocker != null) blocker.enabled = closed;
            if (visuals != null)
            {
                for (var i = 0; i < visuals.Length; i++)
                {
                    if (visuals[i] != null) visuals[i].enabled = closed;
                }
            }
            if (obstacle != null) obstacle.enabled = closed;
        }
    }
}
