using Echoes.Gameplay;
using UnityEngine;

namespace Echoes.UI
{
    /// <summary>
    /// Eco da Queda na Cripta (docs/design/21, cena 2 "Rastrear"): um brilho no chao que o heroi recolhe com a acao Interagir. Quem registra o Eco
    /// no save e o <see cref="StoryDirector"/> (regra do core). Visual provisorio, criado em codigo (a arte final passa pela aprovacao do dono).
    /// </summary>
    public sealed class EchoPickup : MonoBehaviour, IInteractable
    {
        public const string PromptLocKey = "ui.interact.take_echo";

        [SerializeField] float reach = 2.4f;
        [SerializeField] float bobMeters = 0.12f;
        [SerializeField] float bobSpeed = 2f;

        StoryDirector director;
        float baseY;
        bool taken;

        public string EchoId { get; private set; } = string.Empty;

        public bool CanInteract => !taken;
        public string PromptKey => PromptLocKey;
        public Vector3 Position => transform.position;
        public float Reach => reach;

        /// <summary>Cria o brilho provisorio de um Eco em <paramref name="position"/>.</summary>
        public static EchoPickup Spawn(StoryDirector owner, string echoId, Vector3 position)
        {
            var go = new GameObject("Echo_" + echoId);
            go.transform.position = position;
            var pickup = go.AddComponent<EchoPickup>();
            pickup.director = owner;
            pickup.EchoId = echoId;
            pickup.baseY = position.y;

            var orb = GameObject.CreatePrimitive(PrimitiveType.Sphere);
            orb.name = "Orb";
            orb.transform.SetParent(go.transform, false);
            orb.transform.localScale = Vector3.one * 0.45f;
            var collider = orb.GetComponent<Collider>();
            if (collider != null) Destroy(collider);
            var shader = Shader.Find("Universal Render Pipeline/Unlit") ?? Shader.Find("Sprites/Default");
            var color = new Color(0.55f, 0.85f, 1f, 1f);
            if (shader != null)
            {
                var material = new Material(shader) { color = color };
                orb.GetComponent<Renderer>().sharedMaterial = material;
            }

            var glow = new GameObject("Glow").AddComponent<Light>();
            glow.transform.SetParent(go.transform, false);
            glow.type = LightType.Point;
            glow.color = color;
            glow.range = 5f;
            glow.intensity = 2.5f;
            return pickup;
        }

        void Update()
        {
            var p = transform.position;
            p.y = baseY + Mathf.Sin(Time.time * bobSpeed) * bobMeters;
            transform.position = p;
            transform.Rotate(0f, 45f * Time.deltaTime, 0f, Space.World);
        }

        public void Interact()
        {
            if (taken || director == null) return;
            if (!director.CollectEcho(EchoId)) return;
            taken = true;
            gameObject.SetActive(false);
        }
    }
}
