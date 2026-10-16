using UnityEngine;
using UnityEngine.InputSystem;

namespace Echoes.Presentation
{
    /// <summary>
    /// SÓ DESENVOLVIMENTO: troca a distância da câmera 3/4 para o dono comparar o enquadramento.
    /// F1 a F4 aplicam os presets; roda do mouse ou PageUp/PageDown ajustam um passo. Mostra no canto
    /// superior esquerdo a distância, a largura e a profundidade de chão visíveis e a altura do herói em
    /// pixels. Não mexe no <see cref="RenderSettingsAsset"/> (a distância padrão do jogo continua lá).
    /// </summary>
    [DisallowMultipleComponent]
    public sealed class CameraDistanceTuner : MonoBehaviour
    {
        [Tooltip("Câmera filha do CameraRig.")]
        [SerializeField] Camera viewCamera;
        [SerializeField] CameraDistancePresetsAsset presets;
        [Tooltip("Objeto cujos Renderers formam os bounds medidos em pixels (o herói).")]
        [SerializeField] Transform measured;

        Renderer[] measuredRenderers;
        float distance;
        float heroPixels;
        GUIStyle style;

        public float Distance => distance;

        void Awake()
        {
            if (viewCamera == null) viewCamera = GetComponentInChildren<Camera>();
            if (presets == null) presets = ScriptableObject.CreateInstance<CameraDistancePresetsAsset>();
        }

        void Start()
        {
            var index = Mathf.Clamp(presets.initialPreset, 0, presets.presets.Length - 1);
            Apply(presets.presets[index].distance);
        }

        public void Apply(float meters)
        {
            distance = Mathf.Clamp(meters, presets.minDistance, presets.maxDistance);
            if (viewCamera == null) return;
            viewCamera.transform.localPosition = new Vector3(0f, 0f, -distance);
            viewCamera.transform.localRotation = Quaternion.identity;
            viewCamera.fieldOfView = presets.verticalFieldOfView;
            viewCamera.farClipPlane = CameraFootprint.FarClip(distance, presets.farClipMargin);
        }

        void Update()
        {
            var keyboard = Keyboard.current;
            if (keyboard == null) return;
            var count = Mathf.Min(presets.presets.Length, 4);
            for (var i = 0; i < count; i++)
            {
                var key = i == 0 ? keyboard.f1Key : i == 1 ? keyboard.f2Key : i == 2 ? keyboard.f3Key : keyboard.f4Key;
                if (key.wasPressedThisFrame) Apply(presets.presets[i].distance);
            }
            var direction = 0;
            if (keyboard.pageUpKey.wasPressedThisFrame) direction = 1;
            else if (keyboard.pageDownKey.wasPressedThisFrame) direction = -1;
            var mouse = Mouse.current;
            if (mouse != null)
            {
                var scroll = mouse.scroll.ReadValue().y;
                if (scroll > 0.01f) direction = 1;       // roda para cima afasta
                else if (scroll < -0.01f) direction = -1;
            }
            if (direction != 0)
                Apply(CameraFootprint.StepDistance(distance, direction, presets.step, presets.minDistance, presets.maxDistance));
        }

        void LateUpdate()
        {
            heroPixels = MeasureHeroPixels();
        }

        float MeasureHeroPixels()
        {
            if (viewCamera == null || measured == null) return 0f;
            if (measuredRenderers == null || measuredRenderers.Length == 0) measuredRenderers = measured.GetComponentsInChildren<Renderer>();
            if (measuredRenderers.Length == 0) return 0f;
            var bounds = measuredRenderers[0].bounds;
            for (var i = 1; i < measuredRenderers.Length; i++) bounds.Encapsulate(measuredRenderers[i].bounds);
            var min = float.MaxValue;
            var max = float.MinValue;
            var c = bounds.center;
            var e = bounds.extents;
            for (var i = 0; i < 8; i++)
            {
                var corner = c + new Vector3((i & 1) == 0 ? -e.x : e.x, (i & 2) == 0 ? -e.y : e.y, (i & 4) == 0 ? -e.z : e.z);
                var y = viewCamera.WorldToScreenPoint(corner).y;
                if (y < min) min = y;
                if (y > max) max = y;
            }
            return max - min;
        }

        // Painel de desenvolvimento: só números e unidades, sem texto de jogo (não passa por localização).
        void OnGUI()
        {
            if (viewCamera == null) return;
            if (style == null)
            {
                style = new GUIStyle(GUI.skin.label) { fontSize = 12 };
                style.normal.textColor = Color.white;
            }
            var pitch = viewCamera.transform.eulerAngles.x;
            var width = CameraFootprint.VisibleWidth(distance, viewCamera.fieldOfView, viewCamera.aspect);
            var depth = CameraFootprint.VisibleGroundDepth(distance, viewCamera.fieldOfView, pitch);
            var text = $"cam {distance:0} m | chao {width:0.0} x {depth:0.0} m | heroi {heroPixels:0} px | FOV {viewCamera.fieldOfView:0.0} far {viewCamera.farClipPlane:0}";
            // Abaixo do bloco de vida do HUD (canto superior esquerdo).
            var rect = new Rect(8f, 150f, 540f, 22f);
            var previous = GUI.color;
            GUI.color = new Color(0f, 0f, 0f, 0.6f);
            GUI.DrawTexture(rect, Texture2D.whiteTexture);
            GUI.color = previous;
            GUI.Label(rect, text, style);
        }
    }
}
