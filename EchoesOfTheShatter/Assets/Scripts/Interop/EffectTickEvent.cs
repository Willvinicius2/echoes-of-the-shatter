namespace Echoes.Interop
{
    /// <summary>
    /// Evento gerado ao avançar os efeitos de uma entidade (<c>shatter::EffectEvent</c>).
    /// Dano de DoT vem cru: o chamador passa pelo golpe com <c>IsDamageOverTime</c>.
    /// </summary>
    public struct EffectTickEvent
    {
        public bool Expired;
        public string EffectId;
        public DamageByType Damage;
        public SkillTags Tags;
    }
}
