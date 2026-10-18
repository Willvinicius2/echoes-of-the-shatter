namespace Echoes.Interop
{
    /// <summary>
    /// Comportamento em tempo real que os dados de uma habilidade determinam (<c>shatter::SkillBehavior</c>,
    /// <c>ClassifySkill</c>, docs/18 secao 8 item 3). UMA interpretação, no core: o gameplay escolhe a geometria por estes
    /// campos em vez de reler <c>shape</c>, <c>range</c> e <c>radius</c>. Só o núcleo nativo preenche; no stub tudo é false.
    /// </summary>
    public readonly struct SkillBehavior
    {
        /// <summary>(a) Projétil com <see cref="SkillInfo.ExplosionRadiusUu"/> &gt; 0: explode no impacto e acerta todos os alvos da área uma vez (o <see cref="SkillInfo.RadiusUu"/> é só a largura de colisão).</summary>
        public readonly bool Explodes;

        /// <summary>(b) Vários projéteis com ângulo: sai em leque de <see cref="SkillInfo.ConeAngleDegrees"/> graus.</summary>
        public readonly bool Fan;

        /// <summary>(c) Área com alcance 0: centrada em quem usa.</summary>
        public readonly bool SelfCentered;

        /// <summary>(d) Área com alcance &gt; 0: cai no cursor, limitada a <see cref="SkillInfo.RangeUu"/> do herói; o impacto é o atraso até acertar.</summary>
        public readonly bool GroundTargeted;

        /// <summary>(e) Dash com tag projétil: pula <see cref="SkillInfo.RangeUu"/> para trás e atira em <see cref="CombatRules.DashShotRangeUu"/> no pico.</summary>
        public readonly bool DashBackShot;

        public SkillBehavior(bool explodes, bool fan, bool selfCentered, bool groundTargeted, bool dashBackShot)
        {
            Explodes = explodes;
            Fan = fan;
            SelfCentered = selfCentered;
            GroundTargeted = groundTargeted;
            DashBackShot = dashBackShot;
        }
    }
}
