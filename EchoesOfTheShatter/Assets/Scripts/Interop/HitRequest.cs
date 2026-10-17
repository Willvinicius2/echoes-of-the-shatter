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
    }
}
