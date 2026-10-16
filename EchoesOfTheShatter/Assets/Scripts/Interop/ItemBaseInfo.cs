namespace Echoes.Interop
{
    /// <summary>Base de item (<c>shatter::ItemBaseData</c>, item_bases.csv). Só o que o combate usa.</summary>
    public sealed class ItemBaseInfo
    {
        public string Id { get; internal set; } = string.Empty;
        public string Slot { get; internal set; } = string.Empty;
        public int ItemLevel { get; internal set; } = 1;
        public DamageByType WeaponDamage { get; internal set; }
        public double AttackTime { get; internal set; }
        public bool IsWeapon => !WeaponDamage.IsZero;

        public override string ToString() => Id;
    }
}
