using Echoes.Core;
using Echoes.Gameplay;
using UnityEngine;

namespace Echoes.Presentation
{
    /// <summary>
    /// Câmera 3/4 própria, sem Cinemachine (docs/tecnico/04_arquitetura.md, seção 3.2). Fica na raiz
    /// <c>CameraRig</c> (rotação fixa: pitch e yaw); a <see cref="Camera"/> é filha a −distância no Z local.
    /// Segue o alvo com suavização exponencial e atraso máximo; tremor aditivo só em impactos grandes.
    /// </summary>
    [DisallowMultipleComponent]
    public sealed class FollowCamera : MonoBehaviour
    {
        [SerializeField] Transform target;
        [Tooltip("Câmera filha deste rig.")]
        [SerializeField] Camera viewCamera;
        [SerializeField] RenderSettingsAsset settings;
        [Tooltip("Para ouvir os golpes que pedem tremor. Vazio = procura na cena.")]
        [SerializeField] GameRoot root;
        [Tooltip("Opção do jogador: tremor de tela (RF-17).")]
        [SerializeField] bool shakeEnabled = true;

        RenderSettingsAsset runtimeDefaults;
        Vector3 followPosition;
        float shakeAmplitude;
        float shakeTimeLeft;
        float shakeDuration;
        float shakeSeed;
        bool subscribed;

        public bool ShakeEnabled
        {
            get => shakeEnabled;
            set => shakeEnabled = value;
        }

        RenderSettingsAsset Settings
        {
            get
            {
                if (settings != null) return settings;
                if (runtimeDefaults == null) runtimeDefaults = ScriptableObject.CreateInstance<RenderSettingsAsset>();
                return runtimeDefaults;
            }
        }

        void Awake()
        {
            if (viewCamera == null) viewCamera = GetComponentInChildren<Camera>();
            ApplySettings();
            shakeSeed = Random.value * 100f;
            if (target != null) followPosition = target.position + Settings.targetOffset;
        }

        void Start()
        {
            if (root == null) root = FindAnyObjectByType<GameRoot>();
            if (root != null && root.Events != null)
            {
                root.Events.Subscribe<HitEvent>(OnHit);
                subscribed = true;
            }
        }

        void OnDestroy()
        {
            if (subscribed && root != null && root.Events != null) root.Events.Unsubscribe<HitEvent>(OnHit);
            if (runtimeDefaults != null) Destroy(runtimeDefaults);
        }

        void OnValidate()
        {
            // No editor só aplica com o asset ligado (não cria instância temporária fora do Play).
            if (settings == null) return;
            if (viewCamera == null) viewCamera = GetComponentInChildren<Camera>();
            ApplySettings();
        }

        public void SetTarget(Transform newTarget, bool snap)
        {
            target = newTarget;
            if (snap && target != null) followPosition = target.position + Settings.targetOffset;
        }

        /// <summary>Aplica rotação fixa do rig e posição, FOV e planos de corte da câmera filha.</summary>
        public void ApplySettings()
        {
            var s = Settings;
            transform.rotation = Quaternion.Euler(s.pitchDegrees, s.yawDegrees, 0f);
            if (viewCamera == null) return;
            viewCamera.transform.localPosition = new Vector3(0f, 0f, -s.distance);
            viewCamera.transform.localRotation = Quaternion.identity;
            viewCamera.fieldOfView = s.verticalFieldOfView;
            viewCamera.nearClipPlane = s.nearClip;
            viewCamera.farClipPlane = s.farClip;
        }

        /// <summary>
        /// Tremor aditivo (só translação), limitado pelo teto do RenderSettings. A amplitude é em metros na distância
        /// de referência (42 m); a aplicação escala por distância/42 (<see cref="CameraShakeScale"/>).
        /// </summary>
        public void AddShake(float amplitudeMeters, float seconds)
        {
            amplitudeMeters *= Echoes.Core.UserSettings.ShakeFactor; // opcao de acessibilidade: Normal, Reduzido ou Desligado (RF-62)
            if (!shakeEnabled || amplitudeMeters <= 0f || seconds <= 0f) return;
            shakeAmplitude = Mathf.Min(Mathf.Max(shakeAmplitude, amplitudeMeters), Settings.shakeMaxMeters);
            shakeDuration = Mathf.Max(seconds, shakeTimeLeft);
            shakeTimeLeft = shakeDuration;
        }

        void LateUpdate()
        {
            if (target == null) return;
            var s = Settings;
            var dt = Time.deltaTime;
            var desired = target.position + s.targetOffset;
            followPosition = Vector3.Lerp(followPosition, desired, 1f - Mathf.Exp(-s.smoothing * dt));
            var lag = followPosition - desired;
            if (lag.sqrMagnitude > s.maxLagMeters * s.maxLagMeters) followPosition = desired + lag.normalized * s.maxLagMeters;

            var offset = Vector3.zero;
            if (shakeTimeLeft > 0f)
            {
                shakeTimeLeft -= dt;
                var decay = shakeDuration > 0f ? Mathf.Clamp01(shakeTimeLeft / shakeDuration) : 0f;
                var t = Time.time * s.shakeFrequencyHz;
                var distanceNow = viewCamera != null ? Mathf.Abs(viewCamera.transform.localPosition.z) : s.distance;
                var scale = CameraShakeScale.Factor(distanceNow, s.shakeReferenceDistance);
                offset = new Vector3(Mathf.PerlinNoise(shakeSeed, t) - 0.5f, Mathf.PerlinNoise(shakeSeed + 31.7f, t) - 0.5f, 0f)
                         * (2f * shakeAmplitude * decay * scale);
                offset = transform.rotation * offset; // tremor no plano da tela
                if (shakeTimeLeft <= 0f) shakeAmplitude = 0f;
            }
            transform.position = followPosition + offset;
        }

        /// <summary>Tremor mínimo do herói (tiro carregado, Bola de Fogo): amplitude do golpe, duração curta do RenderSettings.</summary>
        public void AddHeroShake(float amplitudeMeters) => AddShake(amplitudeMeters, Settings.shakeHeroHeavySeconds);

        void OnHit(in HitEvent evt)
        {
            if (!evt.Result.Landed || !evt.IsHeavy || evt.Attacker == null) return;
            var s = Settings;
            if (evt.Attacker.IsBoss && evt.Target != null && evt.Target.Team == CombatTeam.Hero) AddShake(s.shakeBossMeters, s.shakeSeconds);
            else if (evt.Attacker.Team == CombatTeam.Hero) AddShake(evt.Result.Critical ? s.shakeHeavyMeters : s.shakeHeavyMeters * 0.7f, evt.Result.Critical ? s.shakeSeconds : s.shakeHeroHeavySeconds);
        }
    }
}
