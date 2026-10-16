// ShatterCore — JSON mínimo (parser estrito RFC 8259 + serializador canônico).
#include "shatter/json.h"

#include <cmath>

#include "numtext.h"

namespace shatter::json {

namespace {
const Value& NullValue() {
    static const Value v;
    return v;
}
const std::string& EmptyString() {
    static const std::string s;
    return s;
}
const Value::Object& EmptyObject() {
    static const Value::Object o;
    return o;
}
const Value::Array& EmptyArray() {
    static const Value::Array a;
    return a;
}
}  // namespace

Value::Value() = default;
Value::Value(std::nullptr_t) {}
Value::Value(bool b) : type_(Type::Bool), b_(b) {}
Value::Value(int v) : type_(Type::Int), i_(v) {}
Value::Value(std::int64_t v) : type_(Type::Int), i_(v) {}
Value::Value(std::uint32_t v) : type_(Type::Int), i_(static_cast<std::int64_t>(v)) {}
Value::Value(double v) : type_(Type::Double), d_(v) {}
Value::Value(const char* s) : type_(Type::String), s_(s ? s : "") {}
Value::Value(std::string s) : type_(Type::String), s_(std::move(s)) {}

Value Value::MakeArray() {
    Value v;
    v.type_ = Type::Array;
    v.arr_ = std::make_unique<Array>();
    return v;
}
Value Value::MakeObject() {
    Value v;
    v.type_ = Type::Object;
    v.obj_ = std::make_unique<Object>();
    return v;
}

Value::Value(const Value& o)
    : type_(o.type_), b_(o.b_), i_(o.i_), d_(o.d_), s_(o.s_) {
    if (o.arr_) arr_ = std::make_unique<Array>(*o.arr_);
    if (o.obj_) obj_ = std::make_unique<Object>(*o.obj_);
}
Value::Value(Value&&) noexcept = default;
Value& Value::operator=(const Value& o) {
    if (this != &o) {
        Value tmp(o);
        *this = std::move(tmp);
    }
    return *this;
}
Value& Value::operator=(Value&&) noexcept = default;
Value::~Value() = default;

bool Value::AsBool(bool fallback) const { return type_ == Type::Bool ? b_ : fallback; }

std::int64_t Value::AsInt(std::int64_t fallback) const {
    if (type_ == Type::Int) return i_;
    if (type_ == Type::Double) {
        if (d_ >= -9.2e18 && d_ <= 9.2e18 && d_ == std::floor(d_)) return static_cast<std::int64_t>(d_);
    }
    return fallback;
}

std::uint64_t Value::AsUInt64(std::uint64_t fallback) const {
    if (type_ == Type::String) {
        std::uint64_t v = 0;
        return detail::ParseUInt64(s_, v) ? v : fallback;
    }
    if (type_ == Type::Int && i_ >= 0) return static_cast<std::uint64_t>(i_);
    return fallback;
}

double Value::AsDouble(double fallback) const {
    if (type_ == Type::Double) return d_;
    if (type_ == Type::Int) return static_cast<double>(i_);
    return fallback;
}

const std::string& Value::AsString() const { return type_ == Type::String ? s_ : EmptyString(); }

std::size_t Value::Size() const {
    if (type_ == Type::Array && arr_) return arr_->size();
    if (type_ == Type::Object && obj_) return obj_->size();
    return 0;
}

const Value& Value::At(std::size_t i) const {
    if (type_ == Type::Array && arr_ && i < arr_->size()) return (*arr_)[i];
    return NullValue();
}

Value& Value::Push(Value v) {
    // Qualquer tipo que não seja array vira array (o conteúdo anterior é descartado).
    if (type_ != Type::Array) *this = MakeArray();
    arr_->push_back(std::move(v));
    return arr_->back();
}

const Value* Value::Find(std::string_view key) const {
    if (type_ != Type::Object || !obj_) return nullptr;
    for (const Member& m : *obj_) {
        if (m.first == key) return &m.second;
    }
    return nullptr;
}

const Value& Value::operator[](std::string_view key) const {
    const Value* p = Find(key);
    return p ? *p : NullValue();
}

Value& Value::Set(std::string key, Value v) {
    if (type_ != Type::Object) *this = MakeObject();
    for (Member& m : *obj_) {
        if (m.first == key) {
            m.second = std::move(v);
            return m.second;
        }
    }
    obj_->emplace_back(std::move(key), std::move(v));
    return obj_->back().second;
}

const Value::Object& Value::Members() const {
    return (type_ == Type::Object && obj_) ? *obj_ : EmptyObject();
}
const Value::Array& Value::Items() const {
    return (type_ == Type::Array && arr_) ? *arr_ : EmptyArray();
}

// ---------------------------------------------------------------------------
// Parser
// ---------------------------------------------------------------------------
namespace {

constexpr int kMaxDepth = 128;

class Parser {
public:
    explicit Parser(std::string_view t) : text_(t) {}

    bool Run(Value& out) {
        SkipWs();
        if (!ParseValue(out, 0)) return false;
        SkipWs();
        if (pos_ != text_.size()) return Fail("trailing characters");
        return true;
    }

    bool Fail(const char* msg) {
        if (!failed_) {
            failed_ = true;
            err_.offset = pos_;
            int line = 1, col = 1;
            for (std::size_t i = 0; i < pos_ && i < text_.size(); ++i) {
                if (text_[i] == '\n') { ++line; col = 1; } else { ++col; }
            }
            err_.line = line;
            err_.column = col;
            err_.message = msg;
        }
        return false;
    }
    const ParseError& Error() const { return err_; }

private:
    void SkipWs() {
        while (pos_ < text_.size()) {
            const char c = text_[pos_];
            if (c == ' ' || c == '\t' || c == '\n' || c == '\r') ++pos_; else break;
        }
    }

    bool ParseValue(Value& out, int depth) {
        if (depth > kMaxDepth) return Fail("nesting too deep");
        if (pos_ >= text_.size()) return Fail("unexpected end");
        const char c = text_[pos_];
        switch (c) {
            case '{': return ParseObject(out, depth);
            case '[': return ParseArray(out, depth);
            case '"': {
                std::string s;
                if (!ParseString(s)) return false;
                out = Value(std::move(s));
                return true;
            }
            case 't': return ParseLiteral("true", Value(true), out);
            case 'f': return ParseLiteral("false", Value(false), out);
            case 'n': return ParseLiteral("null", Value(), out);
            default:
                if (c == '-' || (c >= '0' && c <= '9')) return ParseNumber(out);
                return Fail("unexpected character");
        }
    }

    bool ParseLiteral(const char* lit, Value v, Value& out) {
        const std::string_view l(lit);
        if (text_.substr(pos_, l.size()) != l) return Fail("invalid literal");
        pos_ += l.size();
        out = std::move(v);
        return true;
    }

    bool ParseNumber(Value& out) {
        const std::size_t start = pos_;
        if (text_[pos_] == '-') ++pos_;
        if (pos_ >= text_.size()) return Fail("invalid number");
        if (text_[pos_] == '0') {
            ++pos_;
        } else if (text_[pos_] >= '1' && text_[pos_] <= '9') {
            while (pos_ < text_.size() && text_[pos_] >= '0' && text_[pos_] <= '9') ++pos_;
        } else {
            return Fail("invalid number");
        }
        bool isInt = true;
        if (pos_ < text_.size() && text_[pos_] == '.') {
            isInt = false;
            ++pos_;
            const std::size_t d = pos_;
            while (pos_ < text_.size() && text_[pos_] >= '0' && text_[pos_] <= '9') ++pos_;
            if (pos_ == d) return Fail("invalid number");
        }
        if (pos_ < text_.size() && (text_[pos_] == 'e' || text_[pos_] == 'E')) {
            isInt = false;
            ++pos_;
            if (pos_ < text_.size() && (text_[pos_] == '+' || text_[pos_] == '-')) ++pos_;
            const std::size_t d = pos_;
            while (pos_ < text_.size() && text_[pos_] >= '0' && text_[pos_] <= '9') ++pos_;
            if (pos_ == d) return Fail("invalid number");
        }
        const std::string_view lit = text_.substr(start, pos_ - start);
        if (isInt) {
            std::int64_t iv = 0;
            if (detail::ParseInt64(lit, iv)) {
                out = Value(iv);
                return true;
            }
        }
        double dv = 0.0;
        if (!detail::ParseDouble(lit, dv) || !std::isfinite(dv)) return Fail("number out of range");
        out = Value(dv);
        return true;
    }

    static void AppendUtf8(std::string& s, std::uint32_t cp) {
        if (cp < 0x80) {
            s += static_cast<char>(cp);
        } else if (cp < 0x800) {
            s += static_cast<char>(0xC0 | (cp >> 6));
            s += static_cast<char>(0x80 | (cp & 0x3F));
        } else if (cp < 0x10000) {
            s += static_cast<char>(0xE0 | (cp >> 12));
            s += static_cast<char>(0x80 | ((cp >> 6) & 0x3F));
            s += static_cast<char>(0x80 | (cp & 0x3F));
        } else {
            s += static_cast<char>(0xF0 | (cp >> 18));
            s += static_cast<char>(0x80 | ((cp >> 12) & 0x3F));
            s += static_cast<char>(0x80 | ((cp >> 6) & 0x3F));
            s += static_cast<char>(0x80 | (cp & 0x3F));
        }
    }

    bool ParseHex4(std::uint32_t& out) {
        if (pos_ + 4 > text_.size()) return Fail("invalid unicode escape");
        std::uint32_t v = 0;
        for (int i = 0; i < 4; ++i) {
            const char c = text_[pos_ + static_cast<std::size_t>(i)];
            v <<= 4;
            if (c >= '0' && c <= '9') v |= static_cast<std::uint32_t>(c - '0');
            else if (c >= 'a' && c <= 'f') v |= static_cast<std::uint32_t>(c - 'a' + 10);
            else if (c >= 'A' && c <= 'F') v |= static_cast<std::uint32_t>(c - 'A' + 10);
            else return Fail("invalid unicode escape");
        }
        pos_ += 4;
        out = v;
        return true;
    }

    bool ParseString(std::string& out) {
        ++pos_;  // aspas de abertura
        while (true) {
            if (pos_ >= text_.size()) return Fail("unterminated string");
            const unsigned char c = static_cast<unsigned char>(text_[pos_]);
            if (c == '"') { ++pos_; return true; }
            if (c < 0x20) return Fail("control character in string");
            if (c != '\\') { out += static_cast<char>(c); ++pos_; continue; }
            ++pos_;
            if (pos_ >= text_.size()) return Fail("unterminated escape");
            const char e = text_[pos_++];
            switch (e) {
                case '"': out += '"'; break;
                case '\\': out += '\\'; break;
                case '/': out += '/'; break;
                case 'b': out += '\b'; break;
                case 'f': out += '\f'; break;
                case 'n': out += '\n'; break;
                case 'r': out += '\r'; break;
                case 't': out += '\t'; break;
                case 'u': {
                    std::uint32_t cp = 0;
                    if (!ParseHex4(cp)) return false;
                    if (cp >= 0xD800 && cp <= 0xDBFF) {
                        if (pos_ + 2 > text_.size() || text_[pos_] != '\\' || text_[pos_ + 1] != 'u')
                            return Fail("lone surrogate");
                        pos_ += 2;
                        std::uint32_t lo = 0;
                        if (!ParseHex4(lo)) return false;
                        if (lo < 0xDC00 || lo > 0xDFFF) return Fail("invalid surrogate pair");
                        cp = 0x10000 + ((cp - 0xD800) << 10) + (lo - 0xDC00);
                    } else if (cp >= 0xDC00 && cp <= 0xDFFF) {
                        return Fail("lone surrogate");
                    }
                    AppendUtf8(out, cp);
                    break;
                }
                default: return Fail("invalid escape");
            }
        }
    }

    bool ParseArray(Value& out, int depth) {
        ++pos_;
        out = Value::MakeArray();
        SkipWs();
        if (pos_ < text_.size() && text_[pos_] == ']') { ++pos_; return true; }
        while (true) {
            SkipWs();
            Value item;
            if (!ParseValue(item, depth + 1)) return false;
            out.Push(std::move(item));
            SkipWs();
            if (pos_ >= text_.size()) return Fail("unterminated array");
            if (text_[pos_] == ',') { ++pos_; continue; }
            if (text_[pos_] == ']') { ++pos_; return true; }
            return Fail("expected ',' or ']'");
        }
    }

    bool ParseObject(Value& out, int depth) {
        ++pos_;
        out = Value::MakeObject();
        SkipWs();
        if (pos_ < text_.size() && text_[pos_] == '}') { ++pos_; return true; }
        while (true) {
            SkipWs();
            if (pos_ >= text_.size() || text_[pos_] != '"') return Fail("expected string key");
            std::string key;
            if (!ParseString(key)) return false;
            SkipWs();
            if (pos_ >= text_.size() || text_[pos_] != ':') return Fail("expected ':'");
            ++pos_;
            SkipWs();
            Value v;
            if (!ParseValue(v, depth + 1)) return false;
            out.Set(std::move(key), std::move(v));
            SkipWs();
            if (pos_ >= text_.size()) return Fail("unterminated object");
            if (text_[pos_] == ',') { ++pos_; continue; }
            if (text_[pos_] == '}') { ++pos_; return true; }
            return Fail("expected ',' or '}'");
        }
    }

    std::string_view text_;
    std::size_t pos_ = 0;
    bool failed_ = false;
    ParseError err_;
};

void EscapeString(const std::string& s, std::string& out) {
    out += '"';
    for (const char ch : s) {
        const unsigned char c = static_cast<unsigned char>(ch);
        switch (c) {
            case '"': out += "\\\""; break;
            case '\\': out += "\\\\"; break;
            case '\b': out += "\\b"; break;
            case '\f': out += "\\f"; break;
            case '\n': out += "\\n"; break;
            case '\r': out += "\\r"; break;
            case '\t': out += "\\t"; break;
            default:
                if (c < 0x20) {
                    static const char kHex[] = "0123456789abcdef";
                    out += "\\u00";
                    out += kHex[c >> 4];
                    out += kHex[c & 0x0f];
                } else {
                    out += ch;
                }
        }
    }
    out += '"';
}

void Write(const Value& v, bool pretty, int indent, std::string& out) {
    switch (v.type()) {
        case Type::Null: out += "null"; break;
        case Type::Bool: out += v.AsBool() ? "true" : "false"; break;
        case Type::Int: out += detail::FormatInt64(v.AsInt()); break;
        case Type::Double: {
            const double d = v.AsDouble();
            if (!std::isfinite(d)) out += "null";
            else out += detail::FormatDouble17(d);
            break;
        }
        case Type::String: EscapeString(v.AsString(), out); break;
        case Type::Array: {
            const auto& items = v.Items();
            if (items.empty()) { out += "[]"; break; }
            out += '[';
            for (std::size_t i = 0; i < items.size(); ++i) {
                if (i > 0) out += ',';
                if (pretty) { out += '\n'; out.append(static_cast<std::size_t>(indent + 1) * 2, ' '); }
                Write(items[i], pretty, indent + 1, out);
            }
            if (pretty) { out += '\n'; out.append(static_cast<std::size_t>(indent) * 2, ' '); }
            out += ']';
            break;
        }
        case Type::Object: {
            const auto& mem = v.Members();
            if (mem.empty()) { out += "{}"; break; }
            out += '{';
            for (std::size_t i = 0; i < mem.size(); ++i) {
                if (i > 0) out += ',';
                if (pretty) { out += '\n'; out.append(static_cast<std::size_t>(indent + 1) * 2, ' '); }
                EscapeString(mem[i].first, out);
                out += pretty ? ": " : ":";
                Write(mem[i].second, pretty, indent + 1, out);
            }
            if (pretty) { out += '\n'; out.append(static_cast<std::size_t>(indent) * 2, ' '); }
            out += '}';
            break;
        }
    }
}

}  // namespace

bool Parse(std::string_view text, Value& out, ParseError* err) {
    Parser p(text);
    Value tmp;
    if (!p.Run(tmp)) {
        if (err) *err = p.Error();
        return false;
    }
    out = std::move(tmp);
    return true;
}

std::string Serialize(const Value& v, bool pretty) {
    std::string out;
    Write(v, pretty, 0, out);
    return out;
}

}  // namespace shatter::json
