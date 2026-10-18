using Echoes.Core;
using Echoes.Gameplay;
using UnityEngine;

namespace Echoes.Presentation
{
    /// <summary>
    /// Encolher e esticar (squash and stretch) procedural no impacto, no herói e nos inimigos: ao receber um golpe o corpo achata (menor em Y,
    /// maior em XZ) e volta com mola; no impacto do próprio golpe estica um pouco. Só escala o visual (o filho com o Animator), nunca a lógica.
    /// Desligável: <see cref="GlobalEnabled"/> (opção de acessibilidade) ou o campo do componente.
    /// Valores: os tokens <c>juice</c> ainda não têm squash (docs/arte/03_design_tokens.json); os padrões abaixo são de apresentação e
    /// devem virar <c>juice.squash</c> (pedido ao design system).
    /// </summary>
    [DisallowMultipleComponent]
    [RequireComponent(typeof(AttributeComponent))]
    public sealed class ImpactSquash : MonoBehaviour
    {
        /// <summary>Opção do jogador (Reduzir movimento): desliga em todas as entidades.</summary>
        public static bool GlobalEnabled = true;

        [SerializeField] GameRoot root;
        [SerializeField] bool enabledForThis = true;
        [Tooltip("Alvo do squash: o visual (Animator). Vazio = o primeiro filho com Animator.")]
        [SerializeField] Transform visual;
        [Tooltip("Achatamento ao receber um golpe (fração; 0,12 = 12%).")]
        [SerializeField, Range(0f, 0.4f)] float hitSquash = 0.12f;
        [Tooltip("Esticada no impacto do proprio golpe.")]
        [SerializeField, Range(0f, 0.4f)] float strikeStretch = 0.06f;
        [Tooltip("Duração da volta, em segundos.")]
        [SerializeField, Min(0.02f)] float seconds = 0.14f;

        AttributeComponent attributes;
        Vector3 baseScale = Vector3.one;
        float amount;      // + = achata, - = estica
        float time = 1f;
        float used;
        bool subscribed;

        public bool IsActive => enabledForThis && GlobalEnabled;

        Combatant Self => attributes != null ? attributes.Combatant : null;

        void Awake()
        {
            attributes = GetComponent<AttributeComponent>();
            if (visual == null)
            {
                var animator = GetComponentInChildren<Animator>();
                if (animator != null) visual = animator.transform;
            }
            if (visual != null) baseScale = visual.localScale;
        }

        void Start()
        {
            if (root == null) root = FindAnyObjectByType<GameRoot>();
            if (root == null || root.Events == null) return;
            root.Events.Subscribe<HitEvent>(OnHit);
            root.Events.Subscribe<SkillPhaseEvent>(OnPhase);
            subscribed = true;
        }

        void OnDestroy()
        {
            if (!subscribed || root == null || root.Events == null) return;
            root.Events.Unsubscribe<HitEvent>(OnHit);
            root.Events.Unsubscribe<SkillPhaseEvent>(OnPhase);
        }

        void OnHit(in HitEvent evt)
        {
            if (!ReferenceEquals(evt.Target, Self) || !evt.Result.Landed || evt.Result.TotalDamage <= 0.0) return;
            Pulse(hitSquash);
        }

        void OnPhase(in SkillPhaseEvent evt)
        {
            if (!ReferenceEquals(evt.Owner, Self) || evt.Phase != ActionPhase.Impact) return;
            Pulse(-strikeStretch);
        }

        void Pulse(float value)
        {
            if (!IsActive) return;
            amount = value;
            time = 0f;
        }

        /// <summary>Escala atual do visual para um instante (testavel): mola amortecida de 1 ciclo.</summary>
        public static Vector3 ScaleAt(Vector3 baseScale, float amount, float t01)
        {
            // Mola amortecida: comeca em 'amount' e volta a zero com uma pequena oscilacao.
            var k = amount * Mathf.Exp(-4f * t01) * Mathf.Cos(t01 * Mathf.PI * 1.5f);
            var y = 1f - k;
            var xz = 1f + k * 0.5f; // volume aproximadamente constante
            return new Vector3(baseScale.x * xz, baseScale.y * y, baseScale.z * xz);
        }

        void LateUpdate()
        {
            if (visual == null) return;
            if (!IsActive || time >= 1f)
            {
                if (used != 0f)
                {
                    visual.localScale = baseScale;
                    used = 0f;
                }
                return;
            }
            time = Mathf.Min(1f, time + Time.deltaTime / seconds);
            visual.localScale = ScaleAt(baseScale, amount, time);
            used = amount;
        }
    }
}
