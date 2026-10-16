// ShatterCore — SHA-256 próprio (FIPS 180-4), usado no checksum do save.
// Implementação: src/sha256.cpp. Testar com os vetores do NIST ("" e "abc").
#pragma once

#include <array>
#include <cstddef>
#include <cstdint>
#include <string>
#include <string_view>

namespace shatter {

class Sha256 {
public:
    Sha256();
    void Update(const void* data, std::size_t len);
    void Update(std::string_view s) { Update(s.data(), s.size()); }
    std::array<std::uint8_t, 32> Final();   // depois de Final, o objeto precisa de Reset

    void Reset();

    // Atalho: hex minúsculo de 64 caracteres.
    static std::string HexDigest(std::string_view data);

private:
    void Transform(const std::uint8_t block[64]);
    std::uint32_t h_[8];
    std::uint8_t buf_[64];
    std::uint64_t totalBits_ = 0;
    std::size_t bufLen_ = 0;
};

}  // namespace shatter
