// ShatterCore — leitura e escrita de números independentes de locale (interno).
// Usa std::from_chars / std::to_chars: o Windows em pt-BR usa vírgula decimal em strtod/printf.
#pragma once

#include <charconv>
#include <cstdint>
#include <string>
#include <string_view>
#include <system_error>

namespace shatter::detail {

inline bool ParseDouble(std::string_view s, double& out) {
    if (s.empty()) return false;
    const char* b = s.data();
    const char* e = s.data() + s.size();
    if (*b == '+') return false;  // from_chars não aceita '+'; formato do CSV também não
    double v = 0.0;
    const auto r = std::from_chars(b, e, v, std::chars_format::general);
    if (r.ec != std::errc() || r.ptr != e) return false;
    out = v;
    return true;
}

inline bool ParseInt64(std::string_view s, std::int64_t& out) {
    if (s.empty()) return false;
    const char* b = s.data();
    const char* e = s.data() + s.size();
    std::int64_t v = 0;
    const auto r = std::from_chars(b, e, v, 10);
    if (r.ec != std::errc() || r.ptr != e) return false;
    out = v;
    return true;
}

inline bool ParseUInt64(std::string_view s, std::uint64_t& out) {
    if (s.empty()) return false;
    const char* b = s.data();
    const char* e = s.data() + s.size();
    std::uint64_t v = 0;
    const auto r = std::from_chars(b, e, v, 10);
    if (r.ec != std::errc() || r.ptr != e) return false;
    out = v;
    return true;
}

// Equivalente a "%.17g" em locale "C" (forma canônica do save).
inline std::string FormatDouble17(double v) {
    char buf[64];
    const auto r = std::to_chars(buf, buf + sizeof(buf), v, std::chars_format::general, 17);
    return std::string(buf, r.ptr);
}

inline std::string FormatInt64(std::int64_t v) {
    char buf[32];
    const auto r = std::to_chars(buf, buf + sizeof(buf), v);
    return std::string(buf, r.ptr);
}

inline std::string FormatUInt64(std::uint64_t v) {
    char buf[32];
    const auto r = std::to_chars(buf, buf + sizeof(buf), v);
    return std::string(buf, r.ptr);
}

}  // namespace shatter::detail
