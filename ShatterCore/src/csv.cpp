#include "csv.h"

namespace shatter::detail {

std::vector<std::string_view> SplitView(std::string_view s, char sep) {
    std::vector<std::string_view> out;
    if (s.empty()) return out;
    std::size_t pos = 0;
    while (true) {
        const std::size_t next = s.find(sep, pos);
        if (next == std::string_view::npos) {
            out.push_back(s.substr(pos));
            break;
        }
        out.push_back(s.substr(pos, next - pos));
        pos = next + 1;
    }
    return out;
}

bool ParseCsv(std::string_view text, CsvTable& out, CsvError& err) {
    out = CsvTable();
    if (text.size() >= 3 && static_cast<unsigned char>(text[0]) == 0xEF &&
        static_cast<unsigned char>(text[1]) == 0xBB && static_cast<unsigned char>(text[2]) == 0xBF) {
        text.remove_prefix(3);
    }
    int lineNo = 0;
    bool haveHeader = false;
    std::size_t pos = 0;
    while (pos <= text.size()) {
        std::size_t nl = text.find('\n', pos);
        std::string_view line =
            text.substr(pos, nl == std::string_view::npos ? std::string_view::npos : nl - pos);
        const bool last = (nl == std::string_view::npos);
        pos = last ? text.size() + 1 : nl + 1;
        ++lineNo;
        if (!line.empty() && line.back() == '\r') line.remove_suffix(1);
        if (line.empty()) continue;  // linha em branco
        if (line.find('"') != std::string_view::npos) {
            err.line = lineNo;
            err.message = "E_QUOTE: quotes are not allowed in cells";
            return false;
        }
        std::vector<std::string_view> cells = SplitView(line, ',');
        if (!haveHeader) {
            haveHeader = true;
            out.headerLine = lineNo;
            out.header = std::move(cells);
            continue;
        }
        if (cells.size() != out.header.size()) {
            err.line = lineNo;
            err.message = "E_COLUMNS: expected " + std::to_string(out.header.size()) + " columns, found " +
                          std::to_string(cells.size());
            return false;
        }
        CsvRow row;
        row.line = lineNo;
        row.cells = std::move(cells);
        out.rows.push_back(std::move(row));
    }
    if (!haveHeader) {
        err.line = 1;
        err.message = "E_HEADER: empty file";
        return false;
    }
    return true;
}

}  // namespace shatter::detail
