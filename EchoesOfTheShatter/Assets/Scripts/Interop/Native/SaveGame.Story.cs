using System;
using System.Collections.Generic;
using System.Text;

namespace Echoes.Interop.Native
{
    /// <summary>
    /// Historia da campanha no save (API C shatter_story_*; docs/tecnico/09 secao 15): Ecos da Queda, veredito e Fome. Regras, limites e numeros
    /// sao do core e das tabelas de Story/; aqui so chamadas e leitura do JSON. O veredito e irreversivel: a tela mostra o aviso ANTES de chamar.
    /// Grave o save depois de cada mudanca (auto-save, RF-54). Main thread.
    /// </summary>
    public sealed unsafe partial class SaveGame
    {
        const string StoryBonusSource = "story:verdict";

        static readonly StatId[] StoryBonusStats = { StatId.Life, StatId.Damage, StatId.Armor };

        /// <summary>
        /// Bonus total de atributos dos vereditos, em % (o <c>stat_bonus_pct</c> do core). Nao e gravado: a cena o define a partir de
        /// <see cref="ReadStory"/> ao carregar; <see cref="StatsOfCharacter"/> o soma como "aumentado" em Vida, Dano e Armadura do heroi.
        /// </summary>
        public double StoryStatBonusPct { get; set; }

        /// <summary>Bonus de cura de pocao da Reliquia do Descanso, em % (modificador "aumentado" em PotionEffect).</summary>
        public double StoryPotionEffectPct { get; set; }

        /// <summary>Pontos de elite por mapa com Mancha, congelados no inicio da expedicao idle.</summary>
        public Dictionary<string, double> StoryStainEliteByMap { get; set; } = new Dictionary<string, double>();

        /// <summary>Tabela de loot extra por mapa com Mancha (mapId -> tabela).</summary>
        public Dictionary<string, string> StoryStainLootByMap { get; set; } = new Dictionary<string, string>();

        /// <summary>Copia os efeitos do estado da historia (veredito, relíquia, Mancha) para os campos que o cliente aplica.</summary>
        public void ApplyStoryState(StoryState state)
        {
            StoryStatBonusPct = state.StatBonusPct;
            StoryPotionEffectPct = state.PotionEffectPct;
            StoryStainEliteByMap = new Dictionary<string, double>(state.StainEliteBonusByMap);
            StoryStainLootByMap = new Dictionary<string, string>(state.StainLootTableByMap);
        }

        /// <summary>Registra um Eco achado. <paramref name="isNew"/> = false se ja estava registrado. Eco desconhecido ou save cheio de Ecos: false.</summary>
        public bool StoryRecordEcho(StoryDb story, string echoId, out bool isNew)
        {
            isNew = false;
            var id = NativeBuffers.Utf8(echoId);
            byte fresh = 0;
            int status;
            fixed (byte* p = id) status = ShatterNative.shatter_story_record_echo(story.Raw, Raw, p, (nuint)id.Length, &fresh);
            if (status != 0) return false;
            isNew = fresh != 0;
            return true;
        }

        /// <summary>Aplica o veredito (id de verdicts.csv). So <see cref="VerdictResult.Ok"/> muda o save.</summary>
        public VerdictResult StoryApplyVerdict(StoryDb story, string verdictId)
        {
            var id = NativeBuffers.Utf8(verdictId);
            int result = 0;
            int status;
            fixed (byte* p = id) status = ShatterNative.shatter_story_apply_verdict(story.Raw, Raw, p, (nuint)id.Length, &result);
            return status == 0 ? (VerdictResult)result : VerdictResult.Error;
        }

        /// <summary>
        /// Avisa um evento de missao ("talk" com o id do NPC, "reach_map_boss" com o id do mapa). Devolve quantas missoes foram concluidas agora
        /// (-1 em erro). Ecos e veredito avancam sozinhos nas chamadas proprias. Grave o save se o resultado for maior que 0.
        /// </summary>
        public int StoryQuestEvent(StoryDb story, string type, string target)
        {
            var ty = NativeBuffers.Utf8(type);
            var tg = NativeBuffers.Utf8(target);
            uint completed = 0;
            int status;
            fixed (byte* a = ty)
            fixed (byte* b = tg)
                status = ShatterNative.shatter_story_quest_event(story.Raw, Raw, a, (nuint)ty.Length, b, (nuint)tg.Length, &completed);
            return status == 0 ? (int)completed : -1;
        }

        /// <summary>Fome, bonus, Ecos e vereditos do save. Em erro devolve um estado vazio.</summary>
        public StoryState ReadStory(StoryDb story)
        {
            var raw = story.Raw;
            var save = Raw;
            var status = NativeBuffers.ReadString((byte* o, nuint cap, nuint* needed) =>
                ShatterNative.shatter_story_state_json(raw, save, o, cap, needed), out var json, 1024);
            return status == 0 ? StoryState.FromJson(json) : new StoryState();
        }

        /// <summary>Uma regiao: progresso dos Ecos e as duas opcoes da tela de veredito. Regiao desconhecida: objeto vazio (RegionId vazio).</summary>
        public StoryRegionInfo ReadStoryRegion(StoryDb story, string regionId)
        {
            var raw = story.Raw;
            var save = Raw;
            var region = NativeBuffers.Utf8(regionId);
            int status;
            string json;
            fixed (byte* r = region)
            {
                var regionPtr = (IntPtr)r; // ponteiros fixed nao entram na lambda; o IntPtr entra e volta a byte*
                var regionLen = (nuint)region.Length;
                status = NativeBuffers.ReadString((byte* o, nuint cap, nuint* needed) =>
                    ShatterNative.shatter_story_region_json(raw, save, (byte*)regionPtr, regionLen, o, cap, needed), out json, 1024);
            }
            return status == 0 ? StoryRegionInfo.FromJson(json) : new StoryRegionInfo();
        }

        /// <summary>O golpe do General foi revelado pelos Ecos da regiao?</summary>
        public bool StorySkillRevealed(StoryDb story, string regionId, string skillId)
        {
            var region = NativeBuffers.Utf8(regionId);
            var skill = NativeBuffers.Utf8(skillId);
            byte revealed = 0;
            int status;
            fixed (byte* r = region)
            fixed (byte* s = skill)
                status = ShatterNative.shatter_story_skill_revealed(story.Raw, Raw, r, (nuint)region.Length, s, (nuint)skill.Length, &revealed);
            return status == 0 && revealed != 0;
        }

        static void AddStoryModifier(IntPtr handle, StatId stat, double pct, byte* source, int sourceLength)
        {
            if (pct <= 0.0) return;
            ShatterModifier mod = default;
            mod.value = pct / 100.0;
            mod.stat = (ushort)stat;
            mod.kind = 1; // SHATTER_MOD_INCREASED
            ShatterNative.shatter_statblock_add_modifier(handle, &mod, source, (nuint)sourceLength);
        }

        // Soma o bonus dos vereditos ao bloco de atributos do heroi (modificador "aumentado" pelo core; refazer o bloco o zera e soma de novo).
        void ApplyStoryBonus(NativeStatBlock block)
        {
            if (block == null || (StoryStatBonusPct <= 0.0 && StoryPotionEffectPct <= 0.0)) return;
            var source = Encoding.UTF8.GetBytes(StoryBonusSource);
            var handle = block.Handle.DangerousGetHandle();
            fixed (byte* s = source)
            {
                foreach (var stat in StoryBonusStats)
                    AddStoryModifier(handle, stat, StoryStatBonusPct, s, source.Length);
                AddStoryModifier(handle, StatId.PotionEffect, StoryPotionEffectPct, s, source.Length);
            }
        }
    }
}
