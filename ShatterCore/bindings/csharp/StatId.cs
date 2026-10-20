namespace Echoes.Interop
{
    /// <summary>
    /// Atributos do motor. Mesma ordem e mesmos nomes de <c>shatter::StatId</c> (stats.h).
    /// O índice não vai para disco; CSV e save usam o nome em texto.
    /// </summary>
    public enum StatId : ushort
    {
        Life = 0,
        LifeRegen,
        Resource,
        ResourceRegen,
        Armor,
        EvasionChance,
        BlockChance,
        ResistFire,
        ResistCold,
        ResistLightning,
        Damage,
        AttackSpeed,
        CastSpeed,
        CritChance,
        CritMultiplier,
        MoveSpeed,
        CooldownRecovery,
        AreaOfEffect,
        ProjectileCount,
        DamageTaken,
        PotionEffect,
        Count,
    }
}
