// ShatterCore — RNG determinístico.
// SplitMix64 para derivar seeds; PCG32 (XSH-RR) como gerador de cada fluxo.
// Implementação inline e completa: o mesmo código roda no jogo, no idle e nos testes.
// PROIBIDO no motor: std::rand, std::random_device, std::uniform_*_distribution
// (as distribuições da STL variam entre MSVC/libstdc++/libc++).
#pragma once

#include <cstdint>

namespace shatter {

// Fluxos de RNG separados: mudar o combate não muda o loot.
enum class RngStream : std::uint32_t {
    Combat = 1,  // crítico, evasão, bloqueio, chance de efeito, esquiva da IA
    Loot   = 2,  // raridade, base, afixos, valores, quantidade de ouro
    Events = 3,  // escolha do encontro, elites, modificadores de encontro
    Crafting = 4,  // melhorias do Encantador (docs/16 11.6): semente por (craft_seed, uid, craft_steps, operação); não consome Loot
    Rogue = 5,     // cartas da corrida do roguelike 2D (rogue.h): um gerador por sorteio, índice = nº do sorteio
};

// Passo do SplitMix64 (Steele, Lea, Flood 2014). Avança o estado e devolve 64 bits.
inline std::uint64_t SplitMix64Next(std::uint64_t& state) {
    std::uint64_t z = (state += 0x9E3779B97F4A7C15ull);
    z = (z ^ (z >> 30)) * 0xBF58476D1CE4E5B9ull;
    z = (z ^ (z >> 27)) * 0x94D049BB133111EBull;
    return z ^ (z >> 31);
}

// Mistura sem estado (finalizador do SplitMix64).
inline std::uint64_t Mix64(std::uint64_t x) {
    std::uint64_t s = x;
    return SplitMix64Next(s);
}

// seed_do_fluxo = hash(seed_expedição, fluxo, índice_encontro).
// Estável para sempre: alterar esta função invalida saves com expedição em andamento
// (exigiria bump de save_version + migração que encerra a expedição).
inline std::uint64_t DeriveSeed(std::uint64_t seed, RngStream stream, std::uint64_t index) {
    std::uint64_t h = Mix64(seed ^ 0x45434F534F465348ull);               // "ECOSOFSH"
    h = Mix64(h ^ (static_cast<std::uint64_t>(stream) * 0xD6E8FEB86659FD93ull));
    h = Mix64(h ^ (index + 0x632BE59BD9B4E019ull));
    return h;
}

// PCG32 (O'Neill), variante XSH-RR 64→32.
class Pcg32 {
public:
    Pcg32() { Seed(0x853C49E6748FEA9Bull, 0xDA3E39CB94B95BDBull); }
    explicit Pcg32(std::uint64_t seed, std::uint64_t sequence = 0xDA3E39CB94B95BDBull) { Seed(seed, sequence); }

    // Gerador já posicionado no fluxo de um encontro.
    static Pcg32 ForStream(std::uint64_t expeditionSeed, RngStream stream, std::uint64_t index) {
        const std::uint64_t s = DeriveSeed(expeditionSeed, stream, index);
        return Pcg32(s, Mix64(s ^ 0xA5A5A5A5A5A5A5A5ull));
    }

    void Seed(std::uint64_t seed, std::uint64_t sequence) {
        state_ = 0u;
        inc_ = (sequence << 1u) | 1u;
        NextU32();
        state_ += seed;
        NextU32();
    }

    std::uint32_t NextU32() {
        const std::uint64_t old = state_;
        state_ = old * 6364136223846793005ull + inc_;
        const std::uint32_t xorshifted = static_cast<std::uint32_t>(((old >> 18u) ^ old) >> 27u);
        const std::uint32_t rot = static_cast<std::uint32_t>(old >> 59u);
        return (xorshifted >> rot) | (xorshifted << ((32u - rot) & 31u));
    }

    std::uint64_t NextU64() {
        const std::uint64_t hi = NextU32();
        return (hi << 32) | NextU32();
    }

    // Inteiro uniforme em [0, bound), sem viés (rejeição). bound==0 → 0.
    std::uint32_t NextBelow(std::uint32_t bound) {
        if (bound == 0) return 0;
        const std::uint32_t threshold = (0u - bound) % bound;
        for (;;) {
            const std::uint32_t r = NextU32();
            if (r >= threshold) return r % bound;
        }
    }

    // Inteiro uniforme em [lo, hi] (inclusivo). Se hi < lo, devolve lo.
    std::int32_t RangeInt(std::int32_t lo, std::int32_t hi) {
        if (hi <= lo) return lo;
        const std::uint32_t span = static_cast<std::uint32_t>(static_cast<std::int64_t>(hi) - lo + 1);
        return static_cast<std::int32_t>(static_cast<std::int64_t>(lo) + NextBelow(span));
    }

    // Real uniforme em [0, 1) com 24 bits de mantissa (idêntico em toda plataforma IEEE-754).
    double NextUnit() { return static_cast<double>(NextU32() >> 8) * (1.0 / 16777216.0); }

    // Real uniforme em [lo, hi).
    double RangeReal(double lo, double hi) { return lo + (hi - lo) * NextUnit(); }

    // Sorteio com probabilidade p (p<=0 nunca, p>=1 sempre). SEMPRE consome 1 número,
    // mesmo nos extremos, para a posição do fluxo não depender dos atributos.
    bool Chance(double p) {
        const double u = NextUnit();
        return u < p;
    }

    std::uint64_t State() const { return state_; }
    // ADIÇÃO (docs/tecnico/09_mudancas_contrato.md): estado bruto para atravessar a API C (shatter_rng é uma
    // struct de 2 uint64_t do chamador). FromRaw(State(), Increment()) continua exatamente do mesmo ponto.
    std::uint64_t Increment() const { return inc_; }
    static Pcg32 FromRaw(std::uint64_t state, std::uint64_t increment) {
        Pcg32 r;
        r.state_ = state;
        r.inc_ = increment | 1u;  // o incremento do PCG é sempre ímpar
        return r;
    }

private:
    std::uint64_t state_ = 0;
    std::uint64_t inc_ = 1;
};

}  // namespace shatter
