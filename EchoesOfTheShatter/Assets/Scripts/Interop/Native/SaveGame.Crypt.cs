using System;
using System.Text;

namespace Echoes.Interop.Native
{
    /// <summary>
    /// Core da Cripta (API C 1.7; docs/14 secao 5, docs/09 secao 14): estado do mundo no save, semente da visita, baus, loot de encontro, XP por morte,
    /// nivel do save e Fervor. A formacao dos encontros e o conteudo dos baus sao do core; aqui so chamadas. Main thread.
    /// </summary>
    public sealed unsafe partial class SaveGame
    {
        // ------------------------------------------------------------------------------ estado do mundo

        /// <summary>
        /// Comeca uma visita a area: o core incrementa o contador do save e devolve a semente da visita (o chamador nao a escolhe).
        /// Use a MESMA semente em todos os <see cref="RollEncounter"/> da visita, inclusive depois de voltar a um checkpoint.
        /// </summary>
        public bool BeginAreaVisit(NativeRulesCore rules, string mapId, out ulong visitSeed)
        {
            var map = NativeBuffers.Utf8(mapId);
            ulong seed = 0;
            int status;
            fixed (byte* m = map) status = ShatterNative.shatter_world_begin_visit(rules.DbPointer, Raw, m, (nuint)map.Length, &seed);
            visitSeed = status == 0 ? seed : 0UL;
            return status == 0;
        }

        /// <summary>Objeto da area (bau, parede secreta, atalho; IDs do docs/14 secao 5) ja aberto? Baus abertos, segredos e atalho nao voltam com o checkpoint.</summary>
        public bool IsWorldObjectOpen(string mapId, string objectId)
        {
            var map = NativeBuffers.Utf8(mapId);
            var obj = NativeBuffers.Utf8(objectId);
            byte opened = 0;
            int status;
            fixed (byte* m = map)
            fixed (byte* o = obj)
                status = ShatterNative.shatter_world_object_get(Raw, m, (nuint)map.Length, o, (nuint)obj.Length, &opened);
            return status == 0 && opened != 0;
        }

        /// <summary>Marca o objeto como aberto (ou fechado). Grave o save depois. false se o ID e invalido ou o limite do save estourou.</summary>
        public bool SetWorldObjectOpen(string mapId, string objectId, bool open)
        {
            var map = NativeBuffers.Utf8(mapId);
            var obj = NativeBuffers.Utf8(objectId);
            int status;
            fixed (byte* m = map)
            fixed (byte* o = obj)
                status = ShatterNative.shatter_world_object_set(Raw, m, (nuint)map.Length, o, (nuint)obj.Length, (byte)(open ? 1 : 0));
            return status == 0;
        }

        public WorldAreaInfo WorldState(string mapId)
        {
            var map = NativeBuffers.Utf8(mapId);
            var save = Raw;
            var status = NativeBuffers.ReadString((byte* o, nuint cap, nuint* needed) =>
            {
                fixed (byte* m = map) return ShatterNative.shatter_world_state_json(save, m, (nuint)map.Length, o, cap, needed);
            }, out var json, 256);
            return status == 0 ? WorldAreaInfo.FromJson(json) : new WorldAreaInfo { MapId = mapId };
        }

        // ------------------------------------------------------------------------------ encontros e mapa

        public static MapInfo MapInfoOf(NativeRulesCore rules, string mapId)
        {
            var map = NativeBuffers.Utf8(mapId);
            var db = rules.DbPointer;
            var status = NativeBuffers.ReadString((byte* o, nuint cap, nuint* needed) =>
            {
                fixed (byte* m = map) return ShatterNative.shatter_map_info_json(db, m, (nuint)map.Length, o, cap, needed);
            }, out var json, 512);
            return status == 0 ? MapInfo.FromJson(json) : new MapInfo { MapId = mapId };
        }

        /// <summary>
        /// Sorteia o encontro da visita: n entre min e max por grupo e a elite (chanceElite) por espaco, determinístico pela semente da visita.
        /// Um grupo de n inimigos usa os n primeiros espacos do layout. <paramref name="eliteBonusPct"/>: pontos de elite extras da Mancha (0..100). Encontro desconhecido: null.
        /// </summary>
        public static RolledEncounterInfo RollEncounter(NativeRulesCore rules, string encounterId, ulong visitSeed, int eliteBonusPct = 0)
        {
            var enc = NativeBuffers.Utf8(encounterId);
            var db = rules.DbPointer;
            var status = NativeBuffers.ReadString((byte* o, nuint cap, nuint* needed) =>
            {
                fixed (byte* e = enc) return ShatterNative.shatter_encounter_roll_json_ex(db, e, (nuint)enc.Length, visitSeed, eliteBonusPct, o, cap, needed);
            }, out var json, 512);
            return status == 0 ? RolledEncounterInfo.FromJson(json) : null;
        }

        // ------------------------------------------------------------------------------ baus e loot de encontro

        /// <summary>
        /// Abre o bau: tabela de chests.csv (senao a da area), itens NO CHAO, Ouro e Lascas direto no save, bau marcado como aberto no estado do mundo.
        /// Ja aberto: nada e rolado (JSON vazio, <see cref="ChestOpenResult.AlreadyOpen"/>). O RNG de loot e deste save, o mesmo de <see cref="DropLoot"/>.
        /// Grave o save depois.
        /// </summary>
        public string OpenChest(NativeRulesCore rules, string mapId, string chestId, int areaLevel, int raresAlreadyDropped, int maxRares, ulong seed,
                                out ChestOpenResult result, out string error)
        {
            EnsureLootRng(seed);
            var map = NativeBuffers.Utf8(mapId);
            var chest = NativeBuffers.Utf8(chestId);
            var ctx = new ShatterLootContext { quantity_mult = 1.0, mode = 0, area_level = areaLevel, rares_already_dropped = raresAlreadyDropped, max_rares = maxRares };
            var db = rules.DbPointer;
            var save = Raw;
            var buffer = new byte[2048];
            result = ChestOpenResult.Error;
            for (var attempt = 0; attempt < 3; attempt++)
            {
                var rng = lootRng; // buffer pequeno nao muda nada (nem o rng nem o estado do mundo)
                nuint needed = 0;
                int res = 0;
                ShatterError err = default;
                int status;
                fixed (byte* mp = map)
                fixed (byte* cp = chest)
                fixed (byte* o = buffer)
                    status = ShatterNative.shatter_chest_open(db, save, mp, (nuint)map.Length, cp, (nuint)chest.Length, &ctx, &rng, o, (nuint)buffer.Length, &needed, &res, &err);
                if (status == NativeBuffers.BufferTooSmall)
                {
                    buffer = new byte[Math.Max(1, (int)needed)];
                    continue;
                }
                error = status == 0 ? string.Empty : NativeBuffers.ErrorMessage(ref err);
                if (status != 0) return string.Empty;
                lootRng = rng;
                result = (ChestOpenResult)res;
                return res == 0 ? Encoding.UTF8.GetString(buffer, 0, (int)needed) : string.Empty;
            }
            error = "buffer";
            return string.Empty;
        }

        /// <summary>Loot ao limpar um encontro: rola a areaLootTable do mapa (itens no chao, Ouro e Lascas no save). JSON do loot ou vazio em erro.</summary>
        public string EncounterClearLoot(NativeRulesCore rules, string mapId, int areaLevel, int raresAlreadyDropped, int maxRares, ulong seed, out string error)
        {
            EnsureLootRng(seed);
            var map = NativeBuffers.Utf8(mapId);
            var ctx = new ShatterLootContext { quantity_mult = 1.0, mode = 0, area_level = areaLevel, rares_already_dropped = raresAlreadyDropped, max_rares = maxRares };
            var db = rules.DbPointer;
            var save = Raw;
            var buffer = new byte[2048];
            for (var attempt = 0; attempt < 3; attempt++)
            {
                var rng = lootRng;
                nuint needed = 0;
                ShatterError err = default;
                int status;
                fixed (byte* mp = map)
                fixed (byte* o = buffer)
                    status = ShatterNative.shatter_encounter_clear_loot(db, save, mp, (nuint)map.Length, &ctx, &rng, o, (nuint)buffer.Length, &needed, &err);
                if (status == NativeBuffers.BufferTooSmall)
                {
                    buffer = new byte[Math.Max(1, (int)needed)];
                    continue;
                }
                error = status == 0 ? string.Empty : NativeBuffers.ErrorMessage(ref err);
                if (status != 0) return string.Empty;
                lootRng = rng;
                return Encoding.UTF8.GetString(buffer, 0, (int)needed);
            }
            error = "buffer";
            return string.Empty;
        }

        // ------------------------------------------------------------------------------ XP, nivel e Fervor

        static XpInfo ToXp(in ShatterXpInfo x) => new XpInfo(x.awarded, x.xp_in_level, x.xp_to_next, x.level_before, x.level, x.level_cap);

        /// <summary>
        /// XP de uma morte no jogo manual: (xpBase + xpPerLevel x (nivel - 1)) do enemies.csv x elite x Fervor (<paramref name="fervor"/>), subindo de nivel no save
        /// ate o teto da area. <paramref name="eliteRolled"/>: elite sorteado no encontro (com o modificador); elite fixo e chefe usam o valor do inimigo.
        /// </summary>
        public XpInfo AwardKillXp(NativeRulesCore rules, int characterIndex, string mapId, string enemyId, int monsterLevel, bool eliteRolled, string modifierId, bool fervor, out bool ok)
        {
            var map = NativeBuffers.Utf8(mapId);
            var enemy = NativeBuffers.Utf8(enemyId);
            var mod = NativeBuffers.Utf8(modifierId);
            ShatterXpInfo x = default;
            int status;
            fixed (byte* mp = map)
            fixed (byte* ep = enemy)
            fixed (byte* dp = mod)
                status = ShatterNative.shatter_xp_award_kill(rules.DbPointer, Raw, (nuint)characterIndex, mp, (nuint)map.Length, ep, (nuint)enemy.Length, monsterLevel,
                                                             (byte)(eliteRolled ? 1 : 0), dp, (nuint)mod.Length, (byte)(fervor ? 1 : 0), &x);
            ok = status == 0;
            return ok ? ToXp(x) : default;
        }

        /// <summary>Nivel e XP do personagem no save (o heroi usa este nivel). <paramref name="mapId"/> vazio = teto max_level.</summary>
        public XpInfo CharacterProgress(NativeRulesCore rules, int characterIndex, string mapId = "")
        {
            var map = NativeBuffers.Utf8(mapId);
            ShatterXpInfo x = default;
            int status;
            fixed (byte* mp = map) status = ShatterNative.shatter_character_progress(rules.DbPointer, Raw, (nuint)characterIndex, mp, (nuint)map.Length, &x);
            return status == 0 ? ToXp(x) : default;
        }
    }

    public sealed partial class NativeRulesCore
    {
        /// <summary>Fervor do jogo manual (rules.csv) para a HUD: XP +200%, Ouro e materiais +25%, chance de Raro +100% com os valores do CSV.</summary>
        public unsafe FervorInfo Fervor()
        {
            ShatterFervorInfo f = default;
            var status = ShatterNative.shatter_fervor_get(DbPointer, &f);
            NativeCallException.ThrowIfFailed("shatter_fervor_get", status);
            return new FervorInfo(f.xp_mult, f.gold_mat_mult, f.rare_mult, f.xp_bonus, f.gold_mat_bonus, f.rare_bonus);
        }

        /// <summary>
        /// Como <c>GetActionTiming</c>, com o attackTime da arma equipada (docs/19 N0): os golpes que escalam com arma ficam mais lentos com uma arma
        /// de attackTime maior que o da arma inicial da classe (Martelo mais lento que a Espada). <paramref name="weaponBaseIdOrNull"/> vazio = desarmado.
        /// </summary>
        public unsafe ActionTiming GetActionTimingWithWeapon(IStatBlock stats, SkillInfo skill, string classId, string weaponBaseIdOrNull)
        {
            if (skill == null) return default;
            var native = RequireNative(stats);
            var handle = RequireDb();
            var id = NativeBuffers.Utf8(skill.Id);
            var cls = NativeBuffers.Utf8(classId);
            var weapon = NativeBuffers.Utf8(weaponBaseIdOrNull);
            bool a = false, s2 = false;
            try
            {
                handle.DangerousAddRef(ref a);
                native.Handle.DangerousAddRef(ref s2);
                ShatterActionTiming timing;
                int status;
                fixed (byte* p = id)
                fixed (byte* c = cls)
                fixed (byte* w = weapon)
                    status = ShatterNative.shatter_skill_timing_weapon(handle.DangerousGetHandle(), p, (nuint)id.Length, native.Handle.DangerousGetHandle(),
                                                                       c, (nuint)cls.Length, w, (nuint)weapon.Length, &timing);
                NativeCallException.ThrowIfFailed("shatter_skill_timing_weapon", status);
                return new ActionTiming(timing.windup, timing.impact, timing.recovery);
            }
            finally
            {
                if (s2) native.Handle.DangerousRelease();
                if (a) handle.DangerousRelease();
            }
        }
    }
}
