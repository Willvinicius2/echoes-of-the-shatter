// ShatterCore — mini framework de testes (sem GoogleTest, sem downloads).
//
// Uso:
//   #include "test_framework.h"
//   TEST(stats_increased_sums_before_multiply) {
//       EXPECT_NEAR(shatter::ComputeStatValue(100, 0, 0.5, 1.0), 150.0, 1e-9);
//   }
// Um único arquivo de teste deve conter SHATTER_TEST_MAIN() (tests/main.cpp),
// ou compile com -DSHATTER_TEST_DEFINE_MAIN em exatamente uma unidade.
// Linha de comando do executável:
//   shattercore_tests                 → roda todos
//   shattercore_tests <substring>     → roda só os testes cujo nome contém a substring
//   shattercore_tests --list          → lista os nomes
// Código de saída: 0 se tudo passou; 1 se alguma falha; 2 se o filtro não achou teste.
#pragma once

#include <cmath>
#include <cstdio>
#include <cstring>
#include <exception>
#include <sstream>
#include <string>
#include <type_traits>
#include <vector>

namespace shatter_test {

struct TestCase {
    const char* name;
    void (*fn)();
    const char* file;
    int line;
};

inline std::vector<TestCase>& Registry() {
    static std::vector<TestCase> r;
    return r;
}

// Estado do teste em execução.
inline int& CurrentFailures() {
    static int n = 0;
    return n;
}

struct Registrar {
    Registrar(const char* name, void (*fn)(), const char* file, int line) {
        Registry().push_back({name, fn, file, line});
    }
};

template <typename T>
std::string ToStr(const T& v) {
    std::ostringstream os;
    os.precision(17);
    os << v;
    return os.str();
}
inline std::string ToStr(const std::string& v) { return "\"" + v + "\""; }
inline std::string ToStr(const char* v) { return v ? "\"" + std::string(v) + "\"" : "(null)"; }
inline std::string ToStr(bool v) { return v ? "true" : "false"; }
template <typename E, typename = std::enable_if_t<std::is_enum<E>::value>>
std::string ToStrEnum(E e) { return ToStr(static_cast<long long>(e)); }

inline void ReportFailure(const char* file, int line, const std::string& msg) {
    ++CurrentFailures();
    std::fprintf(stderr, "    FALHA %s:%d: %s\n", file, line, msg.c_str());
}

// Exceção usada por ASSERT_* para abortar o teste atual.
struct AbortTest {};

inline int RunAll(int argc, char** argv) {
    const char* filter = nullptr;
    if (argc > 1) {
        if (std::strcmp(argv[1], "--list") == 0) {
            for (const auto& t : Registry()) std::printf("%s\n", t.name);
            return 0;
        }
        filter = argv[1];
    }
    int run = 0, failed = 0;
    for (const auto& t : Registry()) {
        if (filter && std::strstr(t.name, filter) == nullptr) continue;
        ++run;
        CurrentFailures() = 0;
        try {
            t.fn();
        } catch (const AbortTest&) {
            // falha já registrada
        } catch (const std::exception& e) {
            ReportFailure(t.file, t.line, std::string("excecao: ") + e.what());
        } catch (...) {
            ReportFailure(t.file, t.line, "excecao desconhecida");
        }
        if (CurrentFailures() > 0) {
            ++failed;
            std::printf("[FALHOU] %s\n", t.name);
        } else {
            std::printf("[  OK  ] %s\n", t.name);
        }
    }
    if (run == 0) {
        std::printf("Nenhum teste encontrado%s%s\n", filter ? " para o filtro: " : "", filter ? filter : "");
        return 2;
    }
    std::printf("\n%d testes, %d passaram, %d falharam\n", run, run - failed, failed);
    return failed == 0 ? 0 : 1;
}

}  // namespace shatter_test

#define SHATTER_TEST_CONCAT_(a, b) a##b
#define SHATTER_TEST_CONCAT(a, b) SHATTER_TEST_CONCAT_(a, b)

// Declara e registra um teste. Nome: identificador C++ (snake_case recomendado: modulo_o_que_testa).
#define TEST(name)                                                                          \
    static void SHATTER_TEST_CONCAT(shatter_test_fn_, name)();                              \
    static ::shatter_test::Registrar SHATTER_TEST_CONCAT(shatter_test_reg_, name)(          \
        #name, &SHATTER_TEST_CONCAT(shatter_test_fn_, name), __FILE__, __LINE__);           \
    static void SHATTER_TEST_CONCAT(shatter_test_fn_, name)()

#define EXPECT_TRUE(cond)                                                                   \
    do {                                                                                    \
        if (!(cond)) ::shatter_test::ReportFailure(__FILE__, __LINE__, "EXPECT_TRUE(" #cond ")"); \
    } while (0)

#define EXPECT_FALSE(cond)                                                                  \
    do {                                                                                    \
        if ((cond)) ::shatter_test::ReportFailure(__FILE__, __LINE__, "EXPECT_FALSE(" #cond ")"); \
    } while (0)

#define EXPECT_EQ(a, b)                                                                     \
    do {                                                                                    \
        const auto shatter_va_ = (a); /* cópia: (a) pode ser membro de um temporário */      \
        const auto shatter_vb_ = (b);                                                       \
        if (!(shatter_va_ == shatter_vb_))                                                  \
            ::shatter_test::ReportFailure(__FILE__, __LINE__,                               \
                "EXPECT_EQ(" #a ", " #b "): " + ::shatter_test::ToStr(shatter_va_) +        \
                " != " + ::shatter_test::ToStr(shatter_vb_));                               \
    } while (0)

#define EXPECT_NE(a, b)                                                                     \
    do {                                                                                    \
        const auto shatter_va_ = (a); /* cópia: (a) pode ser membro de um temporário */      \
        const auto shatter_vb_ = (b);                                                       \
        if (shatter_va_ == shatter_vb_)                                                     \
            ::shatter_test::ReportFailure(__FILE__, __LINE__,                               \
                "EXPECT_NE(" #a ", " #b "): ambos = " + ::shatter_test::ToStr(shatter_va_)); \
    } while (0)

// Comparação de enums (ToStr genérico não imprime enum class).
#define EXPECT_ENUM_EQ(a, b)                                                                \
    do {                                                                                    \
        const auto shatter_va_ = (a);                                                       \
        const auto shatter_vb_ = (b);                                                       \
        if (!(shatter_va_ == shatter_vb_))                                                  \
            ::shatter_test::ReportFailure(__FILE__, __LINE__,                               \
                "EXPECT_ENUM_EQ(" #a ", " #b "): " + ::shatter_test::ToStrEnum(shatter_va_) + \
                " != " + ::shatter_test::ToStrEnum(shatter_vb_));                           \
    } while (0)

#define EXPECT_NEAR(a, b, tol)                                                              \
    do {                                                                                    \
        const double shatter_va_ = static_cast<double>(a);                                  \
        const double shatter_vb_ = static_cast<double>(b);                                  \
        const double shatter_vt_ = static_cast<double>(tol);                                \
        if (!(std::fabs(shatter_va_ - shatter_vb_) <= shatter_vt_))                         \
            ::shatter_test::ReportFailure(__FILE__, __LINE__,                               \
                "EXPECT_NEAR(" #a ", " #b ", " #tol "): " + ::shatter_test::ToStr(shatter_va_) + \
                " vs " + ::shatter_test::ToStr(shatter_vb_));                               \
    } while (0)

// Versões que abortam o teste atual na falha.
#define ASSERT_TRUE(cond)                                                                   \
    do {                                                                                    \
        if (!(cond)) {                                                                      \
            ::shatter_test::ReportFailure(__FILE__, __LINE__, "ASSERT_TRUE(" #cond ")");    \
            throw ::shatter_test::AbortTest{};                                              \
        }                                                                                   \
    } while (0)

#define ASSERT_EQ(a, b)                                                                     \
    do {                                                                                    \
        const int shatter_before_ = ::shatter_test::CurrentFailures();                      \
        EXPECT_EQ(a, b);                                                                    \
        if (::shatter_test::CurrentFailures() != shatter_before_) throw ::shatter_test::AbortTest{}; \
    } while (0)

#define FAIL(msg)                                                                           \
    do {                                                                                    \
        ::shatter_test::ReportFailure(__FILE__, __LINE__, std::string("FAIL: ") + (msg));   \
    } while (0)

// main() do executável de testes.
#define SHATTER_TEST_MAIN()                                                                 \
    int main(int argc, char** argv) { return ::shatter_test::RunAll(argc, argv); }

#ifdef SHATTER_TEST_DEFINE_MAIN
SHATTER_TEST_MAIN()
#endif
