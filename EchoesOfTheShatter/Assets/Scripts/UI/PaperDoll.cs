using Echoes.Presentation;
using UnityEngine;

namespace Echoes.UI
{
    /// <summary>
    /// O boneco modular do inventario (docs/16 S-05): uma copia do prefab do heroi longe da cena, vestida pelo mesmo caminho do jogo
    /// (<see cref="HeroVisualEquipment"/>, conjunto visual do core), filmada por uma camera propria para uma RenderTexture que a UI mostra.
    /// Idle em loop (o Animator do prefab). Arrastar gira. Sem o jogo trocar nada aqui: so o <see cref="HeroVisualEquipment.Refresh"/>.
    /// </summary>
    public sealed class PaperDoll : MonoBehaviour
    {
        public const int Width = 384, Height = 576;
        static readonly Vector3 Stage = new Vector3(4000f, 0f, 4000f);

        GameObject doll;
        Camera cam;
        RenderTexture texture;

        public RenderTexture Texture => texture;
        public GameObject Doll => doll;
        public bool HasModularParts { get; private set; }

        public static PaperDoll Create(GameObject prefab)
        {
            var go = new GameObject("PaperDoll");
            var paper = go.AddComponent<PaperDoll>();
            paper.Build(prefab);
            return paper;
        }

        void Build(GameObject prefab)
        {
            transform.position = Stage;
            doll = Instantiate(prefab, Stage, Quaternion.Euler(0f, 20f, 0f), transform);
            doll.name = "Doll";
            foreach (var rb in doll.GetComponentsInChildren<Rigidbody>()) Destroy(rb);
            foreach (var c in doll.GetComponentsInChildren<Collider>()) Destroy(c);
            foreach (var animator in doll.GetComponentsInChildren<Animator>()) animator.updateMode = AnimatorUpdateMode.UnscaledTime; // o jogo pausa com o inventario aberto
            HasModularParts = doll.GetComponentInChildren<ModularCharacter>() != null;

            texture = new RenderTexture(Width, Height, 24, RenderTextureFormat.ARGB32) { antiAliasing = 2, name = "PaperDollRT" };
            var camGo = new GameObject("PaperDollCamera");
            camGo.transform.SetParent(transform, false);
            cam = camGo.AddComponent<Camera>();
            cam.targetTexture = texture;
            cam.clearFlags = CameraClearFlags.SolidColor;
            cam.backgroundColor = new Color(0.075f, 0.067f, 0.094f, 1f);
            cam.fieldOfView = 24f;
            cam.nearClipPlane = 0.3f;
            cam.farClipPlane = 30f;
            camGo.transform.position = Stage + new Vector3(0f, 1.05f, 5.2f);
            camGo.transform.rotation = Quaternion.LookRotation(Stage + new Vector3(0f, 0.95f, 0f) - camGo.transform.position);
            var listener = camGo.GetComponent<AudioListener>();
            if (listener != null) Destroy(listener);
        }

        // O ModularCharacter do boneco veste o starter nas posicoes vazias no proprio Start; reaplica o equipamento do save depois dele.
        System.Collections.IEnumerator Start()
        {
            yield return null;
            yield return null;
            Refresh();
        }

        public void Rotate(float degrees)
        {
            if (doll != null) doll.transform.Rotate(0f, degrees, 0f, Space.World);
        }

        /// <summary>Reaplica o equipamento do save no boneco (mesmo caminho do heroi do jogo).</summary>
        public void Refresh()
        {
            if (doll == null) return;
            foreach (var visual in doll.GetComponentsInChildren<HeroVisualEquipment>()) visual.Refresh();
        }

        void OnDestroy()
        {
            if (texture != null)
            {
                texture.Release();
                Destroy(texture);
            }
        }
    }
}
