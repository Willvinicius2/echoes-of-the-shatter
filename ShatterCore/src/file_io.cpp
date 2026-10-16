// ShatterCore — IFileIO padrão com <fstream>/<filesystem>. Caminhos em UTF-8; sem exceções (error_code).
#include <filesystem>
#include <fstream>
#include <iterator>
#include <system_error>

#include "shatter/save.h"

namespace shatter {

namespace {

namespace fs = std::filesystem;

class StdFileIO final : public IFileIO {
public:
    bool Exists(const std::string& path) override {
        std::error_code ec;
        return fs::is_regular_file(fs::u8path(path), ec);
    }

    bool ReadAll(const std::string& path, std::string& out) override {
        std::ifstream in(fs::u8path(path), std::ios::binary);
        if (!in) return false;
        out.assign(std::istreambuf_iterator<char>(in), std::istreambuf_iterator<char>());
        return !in.bad();
    }

    // Cria pastas que faltam, grava e faz flush. (fsync de disco fica a cargo do SO; ver docs/09.)
    bool WriteAll(const std::string& path, std::string_view data) override {
        const fs::path p = fs::u8path(path);
        std::error_code ec;
        if (p.has_parent_path()) fs::create_directories(p.parent_path(), ec);
        std::ofstream out(p, std::ios::binary | std::ios::trunc);
        if (!out) return false;
        out.write(data.data(), static_cast<std::streamsize>(data.size()));
        out.flush();
        return static_cast<bool>(out);
    }

    bool Copy(const std::string& from, const std::string& to) override {
        std::error_code ec;
        return fs::copy_file(fs::u8path(from), fs::u8path(to), fs::copy_options::overwrite_existing, ec) && !ec;
    }

    bool Rename(const std::string& from, const std::string& to) override {
        std::error_code ec;
        fs::rename(fs::u8path(from), fs::u8path(to), ec);
        return !ec;
    }

    bool Remove(const std::string& path) override {
        std::error_code ec;
        fs::remove(fs::u8path(path), ec);
        return !ec;
    }
};

}  // namespace

std::unique_ptr<IFileIO> MakeStdFileIO() { return std::make_unique<StdFileIO>(); }

}  // namespace shatter
