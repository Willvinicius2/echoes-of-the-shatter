using Echoes.Core;
using Echoes.Interop;
using UnityEngine;

namespace Echoes.Gameplay
{
    /// <summary>
    /// Liga o <see cref="CombatSystem"/> (classe pura) ao ciclo do Unity: cria com os serviços do
    /// <see cref="GameRoot"/> e chama o passo fixo a cada quadro, depois da entrada e antes do
    /// movimento (ordem de execução -900). Não usa FixedUpdate: o acumulador é explícito (seção 6.2).
    /// </summary>
    [DefaultExecutionOrder(-900)]
    [DisallowMultipleComponent]
    public sealed class CombatSystemHost : MonoBehaviour
    {
        [SerializeField] GameRoot root;
        [Tooltip("Hitstop e knockback (dados de apresentação). Vazio = padrões dos tokens.")]
        [SerializeField] CombatFeelSettings feel;
        [Tooltip("Teto de passos fixos por quadro (evita espiral quando um quadro demora).")]
        [SerializeField, Min(1)] int maxStepsPerFrame = 8;

        public CombatSystem Combat { get; private set; }
        public GameRoot Root => root;
        public IRulesCore Rules => root != null && root.Rules != null ? root.Rules.Core : null;
        public EventBus Events => root != null ? root.Events : null;

        void Awake()
        {
            if (root == null) root = FindAnyObjectByType<GameRoot>();
            if (root == null || !root.IsReady)
            {
                Debug.LogError("[Combat] GameRoot ausente ou com regras não carregadas; combate desligado.", this);
                enabled = false;
                return;
            }
            var values = feel != null ? feel.ToValues() : CombatFeelSettings.CreateDefaultValues();
            Combat = new CombatSystem(root.Rules.Core, root.Events, root.RunSeed, values, maxStepsPerFrame);
        }

        void Update()
        {
            Combat?.Tick(Time.deltaTime);
        }

        /// <summary>Procura o host na cena quando a referência não foi ligada no Inspector.</summary>
        public static CombatSystemHost Resolve(CombatSystemHost assigned, Object context)
        {
            if (assigned != null) return assigned;
            var found = FindAnyObjectByType<CombatSystemHost>();
            if (found == null) Debug.LogError("[Combat] Nenhum CombatSystemHost na cena.", context);
            return found;
        }
    }
}
