// ShatterCore — spawner de hordas do roguelike 2D (API 1.11; docs/tecnico/09 seção 18; plano docs/design/31, pacote H3).
//
// O core decide QUEM nasce e QUANDO; o cliente (Godot) só instancia, move e luta. Cada fase (mapa aberto) tem ondas
// contadas em godot/data2d/ondas.csv. Cada onda tem um orçamento de spawn (soma dos custos dos inimigos), um intervalo
// entre lotes, um tamanho de lote, um teto de vivos, uma mistura de tipos com peso e custo e quantos elites marcar.
// godot/data2d/ondas_fases.csv dá as regras da fase: prazo, anel de spawn, chefe, quando ele pode ser acordado e o
// enxame final.
//
// Regras:
// - Relógio inteiro em microssegundos (dt arredondado), para que simular em 1 ou N partes dê o mesmo resultado.
// - Um lote nasce no início da onda e depois a cada `intervalo`. Cada lote solta até `lote` inimigos, sem passar do teto
//   de vivos nem do orçamento que sobra. O tipo é sorteado entre os que cabem no orçamento, pelo peso.
// - Elites: a onda marca `elites` inimigos espalhados pelo orçamento (o k-ésimo quando o gasto chega a k/(elites+1)).
// - A onda passa para a próxima quando o orçamento acabou E (a duração passou OU não há ninguém vivo). A última onda
//   recomeça (com orçamento novo) até o prazo da fase.
// - Prazo (ondas_fases.csv): antes dele, a partir da onda `despertar_onda`, o jogador pode acordar o chefe (WakeBoss).
//   No prazo, as ondas param e começa o enxame final (orçamento, lote, intervalo e teto próprios); o chefe acorda junto
//   se ainda dormia. A fase termina quando o chefe morre (fase sem chefe: enxame gasto e ninguém vivo).
// - Sorteio: Pcg32::ForStream(seed, RngStream::RogueWave, id do spawn), um gerador por inimigo. Mesmo seed + dados +
//   ações (mortes, despertar) nos mesmos instantes = mesmos spawns e mesmo hash.
// - Posição: anel ao redor do jogador. Cada spawn traz um ângulo (radianos, 0 = +x, sentido do eixo y do cliente) e um
//   raio entre raio_min e raio_max da fase. O cliente soma à posição do jogador e prende nas bordas do mapa.
#pragma once

#include <cstdint>
#include <string>
#include <string_view>
#include <vector>

#include "shatter/rogue.h"

namespace shatter {

inline constexpr std::int64_t kRogueWaveStateFormat = 1;
// Maior dt aceito num Tick (s). dt maior é cortado: um lag enorme não solta centenas de lotes de uma vez.
inline constexpr double kRogueWaveMaxTick = 60.0;

enum class RogueWaveResult : std::uint8_t {
    Ok = 0,
    Unknown = 1,     // fase que não existe em ondas.csv
    NotRunning = 2,  // sem fase em andamento
    NotAlive = 3,    // id que não está vivo (já morreu ou nunca nasceu)
    TooEarly = 4,    // acordar o chefe antes da onda despertar_onda
    AlreadyAwake = 5,
    NoBoss = 6,      // fase sem chefe
};

struct RogueWaveSpawn {
    std::uint32_t id = 0;      // 1, 2, 3... na fase (o cliente devolve na morte)
    ContentId enemy;
    bool elite = false;
    bool boss = false;
    int wave = 0;              // 1-based (o enxame final é ondas da fase + 1)
    double angle = 0.0;        // radianos em [0, 2π): direção a partir do jogador
    double radius = 0.0;       // px: distância ao jogador (raio_min..raio_max da fase)
    double hpMult = 1.0;       // elite: elite_vida; senão 1
    double damageMult = 1.0;   // elite: elite_dano; senão 1 (x a curva da onda, API 1.12)
    double speedMult = 1.0;    // curva_horda.csv da onda (API 1.12); 1 sem curva e no chefe
    double xpMult = 1.0;       // idem, para a XP da gema
};

class RogueWaves {
public:
    RogueWaves() = default;
    explicit RogueWaves(const RogueData& data) : data_(&data) {}

    // Começa a fase do zero (descarta a anterior). Unknown se a fase não existe: nada muda.
    RogueWaveResult Start(std::string_view phase, std::uint64_t seed);
    // Encerra a fase (jogador morreu, saiu da corrida). Vivos e fila ficam vazios.
    void Stop();
    // Passa `dt` segundos (<= 0, NaN ou infinito: nada; acima de kRogueWaveMaxTick: cortado). Devolve quantos nasceram
    // agora; os spawns vão para a fila (Pending) até o cliente pegá-los.
    int Tick(double dt);
    const std::vector<RogueWaveSpawn>& Pending() const { return pending_; }
    void ClearPending() { pending_.clear(); }
    // O cliente avisa a morte (ou o sumiço) de um spawn vivo. `out` recebe o spawn que saiu.
    RogueWaveResult Killed(std::uint32_t id, RogueWaveSpawn* out = nullptr);
    // O jogador acorda o chefe (altar do Guardião): ele nasce agora e vai para a fila.
    RogueWaveResult WakeBoss();
    RogueWaveResult CheckWake() const;          // o mesmo resultado, sem mudar nada

    bool Running() const { return phase_ >= 0; }
    bool Complete() const { return complete_; }
    std::string PhaseId() const;                // "" sem fase
    int Wave() const;                           // 1-based; 0 sem fase; ondas + 1 no enxame
    int WavesTotal() const { return count_; }
    bool Swarm() const { return swarm_; }       // enxame final em curso (prazo passou)
    int Loops() const { return loops_; }        // quantas vezes a última onda recomeçou
    const RogueWaveDef* CurrentDef() const;     // nullptr sem fase (no enxame: o enxame)
    const RogueWavePhaseDef* PhaseDef() const { return pdef_; }
    std::int64_t TimeUs() const { return now_; }
    std::int64_t WaveTimeUs() const { return now_ - waveStart_; }
    std::int64_t BudgetLeft() const { return budgetLeft_; }
    bool Exhausted() const;                     // o orçamento da onda atual acabou (nada mais cabe)
    int Alive() const { return static_cast<int>(alive_.size()); }
    const std::vector<RogueWaveSpawn>& AliveList() const { return alive_; }
    bool BossSpawned() const { return bossSpawned_; }
    bool BossAlive() const;
    std::uint32_t SpawnedTotal() const { return spawned_; }
    std::uint32_t KilledTotal() const { return killed_; }
    std::uint64_t Seed() const { return seed_; }

    // Estado canônico (JSON) e hash SHA-256 dele. RestoreState: falha deixa tudo como estava.
    std::string StateJson() const;
    bool RestoreState(std::string_view text, std::string* error = nullptr);
    std::string StateHash() const;

private:
    const RogueWaveDef& Def() const;
    bool LastWave() const { return wave_ + 1 >= count_; }
    void EnterWave(int wave, std::int64_t at);
    void StartSwarm(std::int64_t at);
    void SpawnBatch();
    void SpawnBoss();
    void CheckComplete();
    RogueWaveSpawn MakeSpawn(bool boss);

    const RogueData* data_ = nullptr;
    const RogueWavePhaseDef* pdef_ = nullptr;
    int phase_ = -1;              // índice da 1ª onda da fase em RogueData::Waves(); -1 sem fase
    int count_ = 0;               // ondas da fase
    int wave_ = 0;                // 0-based dentro da fase (= count_ no enxame)
    bool swarm_ = false;
    int loops_ = 0;
    std::uint64_t seed_ = 0;
    std::int64_t now_ = 0;        // µs desde o início da fase
    std::int64_t waveStart_ = 0;
    std::int64_t nextSpawn_ = 0;
    bool waveEndPassed_ = false;
    std::int64_t budgetLeft_ = 0;
    std::int64_t spent_ = 0;      // orçamento gasto na onda
    int elitesSpawned_ = 0;       // na onda
    std::uint32_t spawned_ = 0;   // na fase (= último id)
    std::uint32_t killed_ = 0;
    bool bossSpawned_ = false;
    bool bossKilled_ = false;
    bool complete_ = false;
    std::vector<RogueWaveSpawn> alive_;    // ordem de nascimento
    std::vector<RogueWaveSpawn> pending_;  // nascidos que o cliente ainda não pegou
};

}  // namespace shatter
