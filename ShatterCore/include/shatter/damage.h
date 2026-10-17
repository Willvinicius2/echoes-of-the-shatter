// ShatterCore — resolução de um golpe. Função ÚNICA usada pelo combate em tempo
// real (UE) e pelo simulador idle. Pura: não guarda estado, só lê e devolve.
//
// Ordem de cálculo (plano, seção 10):
//  1. base: para cada tipo de dano, baseDamage[tipo] × coefficient
//     (se a habilidade escala com arma, o chamador já pôs o dano da arma em baseDamage).
//  2. mods por tag: attacker.ApplyTagged(StatId::Damage, skillTags | TagOf(tipo), base)
//  3. crítico: rng.Chance(attacker.GetTagged(CritChance, skillTags)); se critou,
//     × attacker.ApplyTagged(CritMultiplier, skillTags, rules.critMultiplierBase) (base 150%).
//  4. evasão: só se isAttack; chance = min(defender EvasionChance, evasionCap). Evadiu → 0 dano.
//  5. bloqueio: chance = min(defender BlockChance, blockCap). Bloqueou → dano × (1 − blockMitigation).
//  6. armadura: só na parcela física.
//        reduçãoFísica = min(armorMaxReduction, A / (A + k × D))
//        danoFísico    = D × (1 − redução)          (equivale a D² / (D + A/k) sem o teto)
//     com A = defender Armor, D = dano físico do golpe após os passos 1–5, k = armorDamageFactor (5).
//     Ex.: A=500: golpe de 100 → 50% de redução; golpe de 1000 → 9%. Golpe grande passa mais.
//  7. resistência: por tipo elemental, res = clamp(defender Resist*, resistFloor, resistCap);
//     dano × (1 − res).
//  8. dano recebido: × defender.GetTagged(DamageTaken, fromGuardArc ? guard : nenhuma) (base 1). Mods de efeito `guard`
//     (defesa) só entram se o chamador informar que o golpe veio de dentro do arco.
//  9. barreira absorve primeiro; o resto sai da vida. Vida mínima 0.
// Efeitos ao acertar (queimadura, lentidão, quebra de guarda, ganho de recurso)
// NÃO são resolvidos aqui: o chamador aplica depois, se result.landed (ver effects.h).
//
// Consumo de RNG (fluxo Combat): SEMPRE exatamente 3 números, nesta ordem:
// crítico, evasão, bloqueio — mesmo quando a regra não se aplica (ex.: feitiço não
// rola evasão, mas o número é consumido). Assim a posição do fluxo não depende de
// atributos, e trocar um item não "desloca" todos os sorteios seguintes.
// Golpes de DoT (isDamageOverTime) não consomem RNG e pulam 3–5.
#pragma once

#include <array>

#include "shatter/constants.h"
#include "shatter/rng.h"
#include "shatter/stats.h"
#include "shatter/types.h"

namespace shatter {

using DamageArray = std::array<double, kDamageTypeCount>;  // índice = Index(DamageType)

struct HitInput {
    const StatBlock* attacker = nullptr;   // obrigatório
    const StatBlock* defender = nullptr;   // obrigatório
    TagMask skillTags = 0;                 // tags da habilidade (Attack|Melee|Area...)
    DamageArray baseDamage{};              // dano base por tipo, antes do coeficiente
    double coefficient = 1.0;              // coeficiente da habilidade (rank incluso)
    bool isDamageOverTime = false;         // tick de DoT: sem crítico/evasão/bloqueio, sem RNG
    bool canBeBlocked = true;              // falso p/ dano de terreno, por exemplo
    double defenderLife = 0.0;             // vida atual do alvo
    double defenderBarrier = 0.0;          // barreira atual do alvo
    // docs/18 8.1: o cliente faz a geometria (arco da defesa) e diz ao core se ESTE golpe veio de dentro do arco.
    // Os modificadores de DamageTaken de efeitos com a tag guard só valem se true; o resto do defensor não muda.
    bool fromGuardArc = false;
};

enum class HitOutcome : std::uint8_t {
    Hit = 0,
    Evaded = 1,
    Blocked = 2,   // bloqueado (pode ainda causar dano se blockMitigation < 1)
};

struct HitResult {
    HitOutcome outcome = HitOutcome::Hit;
    bool critical = false;
    bool landed = false;            // true se não foi evadido (efeitos ao acertar podem ser aplicados)
    DamageArray afterModifiers{};   // após passos 1–3 (para números de dano e testes)
    DamageArray afterMitigation{};  // após passos 4–8
    double totalDamage = 0.0;       // Σ afterMitigation
    double absorbedByBarrier = 0.0;
    double lifeLost = 0.0;
    double defenderLifeAfter = 0.0;
    double defenderBarrierAfter = 0.0;
    bool killed = false;            // vida chegou a 0 neste golpe (e era > 0 antes)
};

// Resolve um golpe. Implementação: src/damage.cpp.
HitResult ResolveHit(const HitInput& in, const RulesConstants& rules, Pcg32& combatRng);

// Funções de passo isoladas (expostas para testes unitários e tooltips).
double ArmorReduction(double armor, double physicalDamage, const RulesConstants& rules);  // fração [0, armorMaxReduction]
double ClampResistance(double resist, const RulesConstants& rules);                      // [resistFloor, resistCap]

}  // namespace shatter
