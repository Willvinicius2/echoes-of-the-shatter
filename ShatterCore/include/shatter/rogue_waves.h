// ShatterCore — spawner de hordas do roguelike 2D (API 1.11; docs/tecnico/09 seção 18; plano docs/design/31, pacote H3).
//
// O core decide QUEM nasce e QUANDO; o cliente (Godot) só instancia, move e luta. Cada fase (mapa aberto) tem ondas
// contadas em godot/data2d/ondas.csv. Cada onda tem um orçamento de spawn (soma dos custos dos inimigos), um intervalo
// entre lotes, um tamanho de lote, um teto de vivos, uma mistura de tipos com peso e custo, quantos elites marcar e,
// na última onda, o chefe.
//
// Regras:
// - Relógio inteiro em microssegundos (dt arredondado), para que simular em 1 ou N partes dê o mesmo resultado.
// - Um lote nasce no início da onda e depois a cada `intervalo`. Cada lote solta até `lote` inimigos, sem passar do teto
//   de vivos nem do orçamento que sobra. O tipo é sorteado entre os que cabem no orçamento, pelo peso.
// - Elites: a onda marca `elites` inimigos espalhados pelo orçamento (o k-ésimo quando o gasto chega a k/(elites+1)).
// - A onda passa para a próxima quando o orçamento acabou E (a duração passou OU não há ninguém vivo). Na última onda
//   o chefe nasce no início (fora do teto e do orçamento). A fase termina quando o chefe morre; sem chefe, quando o
//   orçamento da última onda acabou e ninguém está vivo.
// - Sorteio: Pcg32::ForStream(seed, RngStream::RogueWave, id do spawn), um gerador por inimigo. Mesmo seed + dados +
//   mortes nos mesmos instantes = mesmos spawns e mesmo hash.
// - Borda e posição: cada spawn traz uma borda (0 norte, 1 leste, 2 sul, 3 oeste) e uma posição 0..1 ao longo dela.
//   O cliente converte em ponto do mapa (fora da tela, perto do jogador).
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
};

struct RogueWaveSpawn {
    std::uint32_t id = 0;      // 1, 2, 3... na fase (o cliente devolve na morte)
    ContentId enemy;
    bool elite = false;
    bool boss = false;
    int wave = 0;              // 1-based
    int edge = 0;              // 0 norte, 1 leste, 2 sul, 3 oeste
    double pos = 0.0;          // 0..1 ao longo da borda
    double hpMult = 1.0;       // elite: elite_vida; senão 1
    double damageMult = 1.0;   // elite: elite_dano; senão 1
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

    bool Running() const { return phase_ >= 0; }
    bool Complete() const { return complete_; }
    std::string PhaseId() const;                // "" sem fase
    int Wave() const;                           // 1-based; 0 sem fase
    int WavesTotal() const { return count_; }
    const RogueWaveDef* CurrentDef() const;     // nullptr sem fase
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
    void SpawnBatch();
    void SpawnBoss();
    void CheckComplete();
    RogueWaveSpawn MakeSpawn(bool boss);

    const RogueData* data_ = nullptr;
    int phase_ = -1;              // índice da 1ª onda da fase em RogueData::Waves(); -1 sem fase
    int count_ = 0;               // ondas da fase
    int wave_ = 0;                // 0-based dentro da fase
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
