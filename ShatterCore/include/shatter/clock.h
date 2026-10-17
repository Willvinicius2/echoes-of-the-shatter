// ShatterCore — tempo offline e relógio não confiável (plano, seção 10).
// Tudo em horário Unix UTC (segundos). O relógio do PC é uma ENTRADA que pode mentir.
// Funções puras e inline: o UE fornece os horários (FDateTime::UtcNow().ToUnixTimestamp()
// e, se houver, ISteamUtils::GetServerRealTime()).
#pragma once

#include <algorithm>
#include <cstdint>

#include "shatter/constants.h"
#include "shatter/types.h"

namespace shatter {

struct ClockInput {
    UnixSeconds localNowUtc = 0;      // relógio do PC
    bool hasSteamTime = false;
    UnixSeconds steamNowUtc = 0;      // ISteamUtils::GetServerRealTime()
    UnixSeconds lastSeenUtc = 0;      // gravado em todo save (0 = save novo)
};

struct TrustedNow {
    UnixSeconds now = 0;
    bool usedSteam = false;           // diferença local × Steam > 10 min → usa a Steam
    bool rollbackDetected = false;    // now < lastSeen − 5 min
};

// Escolhe o "agora" confiável e detecta relógio voltando.
inline TrustedNow ResolveNow(const ClockInput& in, const RulesConstants& r) {
    TrustedNow t;
    t.now = in.localNowUtc;
    if (in.hasSteamTime) {
        const UnixSeconds diff = in.localNowUtc - in.steamNowUtc;
        const UnixSeconds absDiff = diff < 0 ? -diff : diff;
        if (static_cast<double>(absDiff) > r.steamClockMaxSkewSec) {
            t.now = in.steamNowUtc;
            t.usedSteam = true;
        }
    }
    if (in.lastSeenUtc > 0 &&
        static_cast<double>(t.now) < static_cast<double>(in.lastSeenUtc) - r.clockRollbackToleranceSec) {
        t.rollbackDetected = true;
    }
    return t;
}

struct OfflineWindow {
    double effectiveSeconds = 0.0;    // segundos a simular (0..min(duração, teto 12 h))
    bool finished = false;            // a expedição já atingiu a duração escolhida (ou foi encerrada)
    bool endedByRollback = false;     // encerrada no último ponto conhecido (sem tempo extra)
};

// Tempo de expedição a simular.
//  - normal: clamp(now − start, 0, min(duração, maxOfflineHours));
//  - relógio voltou: encerra; tempo = clamp(lastSeen − start, 0, limite) — o último ponto conhecido;
//  - relógio adiantado: o clamp pela duração garante que só antecipa o que já viria.
inline OfflineWindow ComputeExpeditionWindow(UnixSeconds startUtc, int durationHours, const TrustedNow& now,
                                             UnixSeconds lastSeenUtc, const RulesConstants& r) {
    OfflineWindow w;
    const double limit = std::min(static_cast<double>(durationHours) * 3600.0, r.maxOfflineHours * 3600.0);
    UnixSeconds ref = now.now;
    if (now.rollbackDetected) {
        ref = std::max(lastSeenUtc, startUtc);
        w.endedByRollback = true;
    }
    // Em double: o início vem de um save que pode estar adulterado e `ref - startUtc` em int64 estouraria (UB).
    const double elapsed = static_cast<double>(ref) - static_cast<double>(startUtc);
    w.effectiveSeconds = std::clamp(elapsed, 0.0, limit);
    w.finished = w.endedByRollback || elapsed >= limit;
    return w;
}

// Dia UTC (para o descanso diário das Cargas do Marco).
inline std::int64_t UtcDay(UnixSeconds t) {
    return t >= 0 ? t / 86400 : -((-t + 86399) / 86400);
}

// Descanso: +chargesDailyRest por dia real, SEM acumular dias perdidos; respeita o máximo.
// Retorna as cargas novas e atualiza lastRestDay. Relógio voltando nunca concede.
inline int ApplyDailyRest(int charges, std::int64_t& lastRestDay, const TrustedNow& now, const RulesConstants& r) {
    if (now.rollbackDetected) return charges;
    const std::int64_t today = UtcDay(now.now);
    if (today > lastRestDay) {
        lastRestDay = today;
        charges = std::min(r.chargesMax, charges + r.chargesDailyRest);
    }
    return charges;
}

// Novo last_seen: nunca anda para trás (se o relógio voltou, mantém o maior visto).
inline UnixSeconds NextLastSeen(UnixSeconds lastSeen, const TrustedNow& now) {
    return std::max(lastSeen, now.now);
}

}  // namespace shatter
