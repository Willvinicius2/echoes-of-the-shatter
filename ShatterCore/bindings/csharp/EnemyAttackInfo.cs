namespace Echoes.Interop
{
    /// <summary>Ataque de um inimigo (<c>shatter::EnemyAttack</c>, enemy_attacks.csv).</summary>
    public readonly struct EnemyAttackInfo
    {
        public readonly SkillInfo Skill;
        public readonly double Weight;
        public readonly bool Telegraphed;

        public EnemyAttackInfo(SkillInfo skill, double weight, bool telegraphed)
        {
            Skill = skill;
            Weight = weight;
            Telegraphed = telegraphed;
        }
    }
}
