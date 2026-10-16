// ShatterCore — JSON mínimo próprio (sem dependências, sem downloads).
// Escopo: o que o save e as ferramentas precisam. UTF-8; \uXXXX com pares substitutos.
// Números: int64 exato quando o literal é inteiro e cabe; senão double.
// Saída canônica: chaves de objeto na ORDEM DE INSERÇÃO (estável → checksum estável),
// doubles com 17 dígitos significativos ("%.17g"), sem NaN/Inf (viram null e erro).
// Implementação: src/json.cpp (Backend Engineer).
#pragma once

#include <cstdint>
#include <map>
#include <memory>
#include <string>
#include <string_view>
#include <utility>
#include <vector>

namespace shatter::json {

enum class Type : std::uint8_t { Null, Bool, Int, Double, String, Array, Object };

class Value {
public:
    using Array = std::vector<Value>;
    using Member = std::pair<std::string, Value>;
    using Object = std::vector<Member>;   // ordem de inserção preservada

    Value();                               // null
    Value(std::nullptr_t);
    Value(bool b);
    Value(int v);
    Value(std::int64_t v);
    Value(std::uint32_t v);
    Value(double v);
    Value(const char* s);
    Value(std::string s);
    static Value MakeArray();
    static Value MakeObject();

    Value(const Value&);
    Value(Value&&) noexcept;
    Value& operator=(const Value&);
    Value& operator=(Value&&) noexcept;
    ~Value();

    Type type() const { return type_; }
    bool IsNull() const { return type_ == Type::Null; }
    bool IsNumber() const { return type_ == Type::Int || type_ == Type::Double; }

    // Leitura tolerante: devolve `fallback` se o tipo não bater.
    bool AsBool(bool fallback = false) const;
    std::int64_t AsInt(std::int64_t fallback = 0) const;   // Double com parte inteira exata também vale
    std::uint64_t AsUInt64(std::uint64_t fallback = 0) const; // aceita string decimal (seeds de 64 bits)
    double AsDouble(double fallback = 0.0) const;           // Int convertido
    const std::string& AsString() const;                     // "" se não for string

    // Array
    std::size_t Size() const;                                // 0 se não for array/objeto
    const Value& At(std::size_t i) const;                    // null estático se fora
    Value& Push(Value v);                                    // converte null em array

    // Objeto
    const Value* Find(std::string_view key) const;           // nullptr se ausente
    const Value& operator[](std::string_view key) const;     // null estático se ausente
    Value& Set(std::string key, Value v);                    // substitui se existir; converte null em objeto
    bool Has(std::string_view key) const { return Find(key) != nullptr; }
    const Object& Members() const;                           // vazio se não for objeto
    const Array& Items() const;                              // vazio se não for array

private:
    Type type_ = Type::Null;
    bool b_ = false;
    std::int64_t i_ = 0;
    double d_ = 0.0;
    std::string s_;
    std::unique_ptr<Array> arr_;
    std::unique_ptr<Object> obj_;
};

struct ParseError {
    std::size_t offset = 0;   // byte
    int line = 1;
    int column = 1;
    std::string message;
};

// Parser estrito (RFC 8259): sem comentários, sem vírgula final, profundidade máx. 128.
bool Parse(std::string_view text, Value& out, ParseError* err = nullptr);

// pretty = true: indentação de 2 espaços e '\n' (o save é legível para depuração).
std::string Serialize(const Value& v, bool pretty = false);

// Uint64 vai como STRING decimal (JSON/double perde precisão acima de 2^53).
inline Value FromUInt64(std::uint64_t v) { return Value(std::to_string(v)); }

}  // namespace shatter::json
