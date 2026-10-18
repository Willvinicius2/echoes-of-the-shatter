// ShatterCore — leitor de CSV do conteúdo (interno). UTF-8, vírgula, 1ª linha = cabeçalho.
// Aceita LF e CRLF e ignora BOM e linhas em branco (a numeração de linhas continua exata).
// Sem aspas: célula com '"' é erro (convenção do docs/tecnico/06_dados.md, E_QUOTE).
#pragma once

#include <string>
#include <string_view>
#include <vector>

namespace shatter::detail {

struct CsvRow {
    int line = 0;                         // 1-based (cabeçalho = 1)
    std::vector<std::string_view> cells;  // views no texto original
};

struct CsvTable {
    int headerLine = 1;
    std::vector<std::string_view> header;
    std::vector<CsvRow> rows;
};

struct CsvError {
    int line = 0;
    std::string message;
};

// Retorna false e preenche `err` no primeiro erro estrutural (aspas, nº de colunas).
bool ParseCsv(std::string_view text, CsvTable& out, CsvError& err);

// Quebra `s` por `sep`; devolve views. Texto vazio -> lista vazia.
std::vector<std::string_view> SplitView(std::string_view s, char sep);

}  // namespace shatter::detail
