namespace Echoes.Gameplay
{
    /// <summary>Por que um comando foi negado (a UI mostra o aviso pela chave de localização).</summary>
    public enum DenyReason : byte
    {
        NoResource = 0,
        Cooldown = 1,
        NoDodgeCharges = 2,
        PotionEmpty = 3,
        Locked = 4,
        EmptySlot = 5,
        Hunger = 6,
    }
}
