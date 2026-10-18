namespace Echoes.Interop
{
    /// <summary>
    /// Entrada de um golpe (<c>shatter::HitInput</c>, damage.h). Na fachada os atributos vão como
    /// <see cref="IStatBlock"/>; a implementação P/Invoke troca pelo handle nativo ao montar a
    /// struct blittable. Struct sem alocação: pode ser montada a cada golpe.
    /// </summary>
    public struct HitRequest
    {
        public IStatBlock Attacker;
        public IStatBlock Defender;
        public SkillTags SkillTags;
        public DamageByType BaseDamage;
        public double Coefficient;
        public bool IsDamageOverTime;
        public bool CanBeBlocked;
        public double DefenderLife;
        public double DefenderBarrier;

        /// <summary>
        /// docs/18 8.1: ESTE golpe veio de dentro do arco da defesa do alvo (o C# faz a geometria, <c>ShapeQuery</c>). Só então valem os
        /// modificadores de dano recebido dos efeitos de defesa (tag <see cref="SkillTags.Guard"/>). Os demais não dependem disto.
        /// Padrão false = fora do arco.
        /// </summary>
        public bool FromGuardArc;

        /// <summary>
        /// Progresso da carga do ATAQUE FORTE, de 0 (carga mínima) a 1 (máxima). O CORE calcula o multiplicador de dano
        /// (<c>1 + (heavyMaxMult - 1) * ChargeFraction</c>, com o <see cref="BasicKitInfo.HeavyMaxMultiplier"/> da classe) e o aplica como
        /// <c>more</c> só neste golpe: o C# NÃO escala o coeficiente. Exige <see cref="ClassId"/>. Fora de 0 a 1 (ou NaN) o core recusa e
        /// <c>ResolveHit</c> lança <c>NativeCallException</c> (INVALID_ARGUMENT). Golpe que não é o forte: deixe 0 e <see cref="ClassId"/> vazio.
        /// </summary>
        public double ChargeFraction;

        /// <summary>Classe de quem desfere o golpe forte (para achar o kit); só lido quando <see cref="ChargeFraction"/> != 0 ou <see cref="IsHeavy"/>.</summary>
        public string ClassId;

        /// <summary>true = golpe forte: usa o caminho de carga mesmo com <see cref="ChargeFraction"/> 0 (carga mínima, multiplicador 1).</summary>
        public bool IsHeavy;
    }
}
