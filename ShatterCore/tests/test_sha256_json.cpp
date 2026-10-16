// SHA-256 (vetores do NIST) e JSON mínimo.
#include <limits>

#include "test_util.h"

using namespace shatter;

TEST(sha256_nist_vectors) {
    EXPECT_EQ(Sha256::HexDigest(""), std::string("e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"));
    EXPECT_EQ(Sha256::HexDigest("abc"), std::string("ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"));
    EXPECT_EQ(Sha256::HexDigest("abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq"),
              std::string("248d6a61d20638b8e5c026930c3e6039a33ce45964ff2167f6ecedd419db06c1"));
    // Milhão de 'a' (atravessa muitos blocos) e atualização em pedaços.
    Sha256 s;
    const std::string chunk(1000, 'a');
    for (int i = 0; i < 1000; ++i) s.Update(chunk);
    const auto d = s.Final();
    static const char kHex[] = "0123456789abcdef";
    std::string hex;
    for (std::uint8_t b : d) { hex += kHex[b >> 4]; hex += kHex[b & 15]; }
    EXPECT_EQ(hex, std::string("cdc76e5c9914fb9281a1c7e284d73e67f1809a48a497200e046d39ccc7112cd0"));
    s.Reset();
    s.Update("a");
    s.Update("bc");
    const auto d2 = s.Final();
    EXPECT_EQ(static_cast<int>(d2[0]), 0xba);
}

TEST(json_parse_and_roundtrip) {
    json::Value v;
    json::ParseError err;
    const std::string src = R"({"a":1,"b":[true,false,null,"x\n\u00e9\ud83d\ude00"],"c":{"d":-2.5e3,"e":9007199254740993},"f":""})";
    EXPECT_TRUE(json::Parse(src, v, &err));
    EXPECT_EQ(v["a"].AsInt(), static_cast<std::int64_t>(1));
    EXPECT_TRUE(v["b"].At(0).AsBool());
    EXPECT_TRUE(v["b"].At(2).IsNull());
    EXPECT_EQ(v["b"].At(3).AsString(), std::string("x\n\xC3\xA9\xF0\x9F\x98\x80"));
    EXPECT_NEAR(v["c"]["d"].AsDouble(), -2500.0, 1e-12);
    EXPECT_EQ(v["c"]["e"].AsInt(), static_cast<std::int64_t>(9007199254740993LL));  // int64 exato
    EXPECT_TRUE(v["missing"].IsNull());
    EXPECT_FALSE(v.Has("missing"));
    // Saída canônica: ordem de inserção, compacta; reparse dá os mesmos bytes.
    const std::string out = json::Serialize(v, false);
    json::Value v2;
    EXPECT_TRUE(json::Parse(out, v2));
    EXPECT_EQ(json::Serialize(v2, false), out);
    const std::string pretty = json::Serialize(v, true);
    json::Value v3;
    EXPECT_TRUE(json::Parse(pretty, v3));
    EXPECT_EQ(json::Serialize(v3, false), out);
}

TEST(json_canonical_numbers_and_key_order) {
    json::Value o = json::Value::MakeObject();
    o.Set("z", json::Value(1));
    o.Set("a", json::Value(0.1));
    o.Set("m", json::Value(3600.0));
    o.Set("s", json::Value(std::string("q\"\\\t\x01")));
    EXPECT_EQ(json::Serialize(o, false), std::string("{\"z\":1,\"a\":0.10000000000000001,\"m\":3600,\"s\":\"q\\\"\\\\\\t\\u0001\"}"));
    o.Set("z", json::Value(2));  // substitui sem mudar a posição
    EXPECT_EQ(o.Members()[0].first, std::string("z"));
    EXPECT_EQ(o["z"].AsInt(), static_cast<std::int64_t>(2));
    EXPECT_EQ(json::Serialize(json::Value(std::numeric_limits<double>::infinity()), false), std::string("null"));
    EXPECT_EQ(json::FromUInt64(18446744073709551615ull).AsUInt64(), 18446744073709551615ull);
}

TEST(json_strict_rejects_invalid) {
    const char* bad[] = {"", "{", "[1,]", "{\"a\":1,}", "{'a':1}", "01", "1.", "-", "+1", ".5", "\"abc", "[1 2]",
                         "{\"a\" 1}", "tru", "nul", "\"\\x\"", "\"\\ud800\"", "\"a\nb\"", "1 2", "// c\n1", "[NaN]", "1e999"};
    for (const char* s : bad) {
        json::Value v;
        if (json::Parse(s, v)) FAIL(std::string("aceitou JSON inválido: ") + s);
    }
    json::Value v;
    json::ParseError err;
    EXPECT_FALSE(json::Parse("{\n  \"a\": ?\n}", v, &err));
    EXPECT_EQ(err.line, 2);
    // Profundidade máxima 128.
    EXPECT_TRUE(json::Parse(std::string(128, '[') + std::string(128, ']'), v));
    EXPECT_FALSE(json::Parse(std::string(200, '[') + std::string(200, ']'), v));
}

TEST(json_accessors_tolerant) {
    json::Value v;
    EXPECT_TRUE(json::Parse(R"({"i":3.0,"s":"18446744073709551615","t":"x"})", v));
    EXPECT_EQ(v["i"].AsInt(), static_cast<std::int64_t>(3));
    EXPECT_EQ(v["s"].AsUInt64(), 18446744073709551615ull);
    EXPECT_EQ(v["t"].AsInt(7), static_cast<std::int64_t>(7));
    EXPECT_EQ(v["t"].AsString(), std::string("x"));
    EXPECT_EQ(v["i"].AsString(), std::string(""));
    json::Value a;
    a.Push(json::Value(1));
    a.Push(json::Value(2));
    EXPECT_EQ(a.Size(), static_cast<std::size_t>(2));
    EXPECT_EQ(a.At(1).AsInt(), static_cast<std::int64_t>(2));
    EXPECT_TRUE(a.At(5).IsNull());
}
