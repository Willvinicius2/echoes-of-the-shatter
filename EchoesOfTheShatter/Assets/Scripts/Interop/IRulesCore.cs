using System;
using System.Collections.Generic;

namespace Echoes.Interop
{
    /// <summary>
    /// Fachada que o jogo usa para pedir regras ao ShatterCore. É o ÚNICO caminho do C# até as
    /// regras (docs/04_arquitetura.md, seções 5, 9 e 10.2): nada de fórmula fora daqui.
    ///
    /// Implementações:
    /// <list type="bullet">
    /// <item><c>StubRulesCore</c> (pasta Stub/): PROVISÓRIA, C# puro, lê os mesmos CSV. Existe só
    /// para o jogo rodar antes da DLL.</item>
    /// <item>A implementação P/Invoke sobre <c>shatter_c.h</c> (agente de Integração) substitui o stub
    /// sem mudar esta interface.</item>
    /// </list>
    /// Pertence à thread principal, exceto as consultas de conteúdo (somente leitura).
    /// </summary>
    public interface IRulesCore : IDisposable
    {
        /// <summary>Versão da API (<c>shatter_api_version</c>); 0 no stub.</summary>
        uint ApiVersion { get; }

        /// <summary>Nome da implementação para o log (ex.: "stub-csharp").</summary>
        string ImplementationName { get; }

        /// <summary>true enquanto a implementação for provisória (stub). A UI de desenvolvimento avisa.</summary>
        bool IsProvisional { get; }

        /// <summary>
        /// Carrega e valida os CSV da pasta (<c>shatter_db_load_directory</c>). Erros vão para
        /// <paramref name="errors"/>; o jogo não inicia com erro.
        /// </summary>
        RulesStatus LoadContent(string dataDirectory, List<RulesError> errors);

        bool IsLoaded { get; }

        /// <summary>
        /// Avisos da última carga que não impedem o jogo (no stub: valores provisórios de docs/13 em uso
        /// porque a chave ou coluna ainda não existe no CSV). O RulesService manda para o log.
        /// </summary>
        IReadOnlyList<string> LoadWarnings { get; }

        uint ContentVersion { get; }

        CombatRules Combat { get; }

        ClassInfo FindClass(string id);
        SkillInfo FindSkill(string id);
        EnemyInfo FindEnemy(string id);
        ItemBaseInfo FindItemBase(string id);
        PotionInfo FindPotion(string id);

        /// <summary>Poções disponíveis em ordem estável (tecla 1, tecla 2).</summary>
        IReadOnlyList<PotionInfo> Potions { get; }

        IStatBlock CreateHeroStats(in HeroBuild build);
        IStatBlock CreateEnemyStats(string enemyId, int level);

        /// <summary>Atributos sem base nem modificador: fonte neutra para dano de efeito (DoT) e de terreno.</summary>
        IStatBlock CreateEmptyStats();

        /// <summary>Contêiner de efeitos de uma entidade; <paramref name="enemyOrNull"/> define imunidades.</summary>
        IEffectSet CreateEffectSet(IStatBlock target, EnemyInfo enemyOrNull);

        /// <summary><paramref name="rolledElite"/>: elite sorteado (<see cref="RollElite"/>), imune ao stun como o chefe e o elite fixo.</summary>
        IEffectSet CreateEffectSet(IStatBlock target, EnemyInfo enemyOrNull, bool rolledElite);

        /// <summary>Cinto de poções do herói (cargas, recarga em série, trava global, carga por elite). Descartar com Dispose.</summary>
        IPotionBelt CreatePotionBelt();

        /// <summary>Cargas e i-frames da esquiva do herói. Descartar com Dispose.</summary>
        IDodgeCharges CreateDodge();

        /// <summary>Sorteia o modificador de elite (consome SEMPRE 1 número do fluxo de eventos <paramref name="eventsRng"/>).</summary>
        EliteProfile RollElite(ref RngState eventsRng);

        /// <summary>Elite com modificador conhecido (elite fixo: o <c>modifierId</c> do enemies.csv); vazio = só os multiplicadores base.</summary>
        EliteProfile GetEliteProfile(string modifierId, bool rolled);

        /// <summary>Escreve os multiplicadores do elite no bloco do inimigo e devolve a barreira inicial.</summary>
        double ApplyElite(IStatBlock enemyStats, in EliteProfile profile);

        /// <summary>Máquina de fases do chefe (escudo frontal, rugido, invocação, padrões). O stub não tem: lança NotSupportedException.</summary>
        IBossController CreateBoss(string enemyId, int level, ulong seed);

        /// <summary>false no stub: o gameplay usa a IA comum no lugar do <see cref="IBossController"/>.</summary>
        bool SupportsBoss { get; }

        /// <summary>Gerador já posicionado no fluxo (<c>Pcg32::ForStream</c>).</summary>
        RngState CreateRng(ulong seed, RngStream stream, ulong index);
        uint NextBelow(ref RngState rng, uint bound);
        double NextUnit(ref RngState rng);

        /// <summary>Escolha ponderada do próximo ataque do inimigo (fluxo de eventos).</summary>
        int PickAttack(ref RngState rng, EnemyInfo enemy);

        /// <summary>Resolve um golpe (<c>shatter_resolve_hit</c>). Consome sempre 3 números do fluxo de combate.</summary>
        HitResult ResolveHit(in HitRequest request, ref RngState combatRng);

        /// <summary>Dano base do golpe: o da arma se a habilidade escala com arma, senão o da habilidade.</summary>
        DamageByType GetSkillBaseDamage(SkillInfo skill, ItemBaseInfo weaponOrNull);

        /// <summary>Tempos das 3 fases com a velocidade de ataque/conjuração aplicada.</summary>
        ActionTiming GetActionTiming(IStatBlock stats, SkillInfo skill);

        /// <summary>
        /// Como <see cref="GetActionTiming(IStatBlock, SkillInfo)"/> para um elite com modificador: o telegraph não encurta com a velocidade
        /// de ataque do modificador (Veloz) e a recuperação usa o <c>recoveryMult</c> dele. <paramref name="eliteModifierIdOrNull"/> vazio = comum.
        /// </summary>
        ActionTiming GetActionTiming(IStatBlock stats, SkillInfo skill, string eliteModifierIdOrNull);

        /// <summary><c>EffectiveCooldown</c> do effects.h (mínimo <c>cooldown_min</c>).</summary>
        double GetEffectiveCooldown(IStatBlock stats, SkillInfo skill);

        double GetEffectiveCost(IStatBlock stats, SkillInfo skill);

        /// <summary>Velocidade final de movimento em uu/s (base × atributo MoveSpeed).</summary>
        double GetMoveSpeedUu(IStatBlock stats, double baseMoveSpeedUu);

        /// <summary>false enquanto a entidade estiver impedida de agir (atordoamento zera a velocidade de ataque).</summary>
        bool CanAct(IStatBlock stats);

        /// <summary>false enquanto a entidade estiver impedida de andar (atordoamento zera a velocidade de movimento).</summary>
        bool CanMove(IStatBlock stats);

        /// <summary>Vida cheia; recurso no valor de repouso da classe.</summary>
        Vitals CreateVitals(IStatBlock stats, ClassInfo classOrNull);

        /// <summary>Regeneração de vida, decaimento do recurso fora de combate e fim da barreira temporária.</summary>
        void TickVitals(ref Vitals vitals, IStatBlock stats, ClassInfo classOrNull, double dt, bool inCombat);

        void GainResource(ref Vitals vitals, IStatBlock stats, double amount);

        bool TrySpendResource(ref Vitals vitals, double amount);

        PotionOutcome ResolvePotion(PotionInfo potion, IStatBlock stats, in Vitals vitals);
    }
}
