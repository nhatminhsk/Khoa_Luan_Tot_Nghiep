package vn.kltn.bankadvisor.module.dataset.importer;

import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Component;
import tools.jackson.databind.MappingIterator;
import tools.jackson.dataformat.csv.CsvMapper;
import tools.jackson.dataformat.csv.CsvSchema;

import java.io.IOException;
import java.io.Reader;
import java.io.UncheckedIOException;
import java.math.BigDecimal;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.sql.Date;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.stream.Collectors;

/**
 * Đọc một file CSV và nạp vào bảng theo {@link TableSpec}.
 * <p>
 * Tên bảng và tên cột trong câu SQL đều lấy từ hằng số trong {@link ServingDatasets}, không lấy từ dữ liệu,
 * nên ghép chuỗi SQL ở đây không có nguy cơ SQL injection. Giá trị luôn truyền qua tham số {@code ?}.
 */
@Component
public class CsvTableLoader {

    private static final int BATCH_SIZE = 1_000;

    private final JdbcTemplate jdbc;
    private final CsvMapper csvMapper = new CsvMapper();

    public CsvTableLoader(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    /** @param skipped số dòng bỏ qua vì mã ngân hàng / chỉ tiêu / chương trình không có trong bảng tham chiếu */
    public record LoadResult(int loaded, int skipped) {
    }

    public List<Map<String, String>> read(Path file) {
        CsvSchema schema = CsvSchema.emptySchema().withHeader();
        try (Reader reader = Files.newBufferedReader(file, StandardCharsets.UTF_8);
             MappingIterator<Map<String, String>> rows = csvMapper.readerForMapOf(String.class).with(schema)
                     .readValues(reader)) {
            return rows.readAll();
        } catch (IOException e) {
            throw new UncheckedIOException("Không đọc được " + file.getFileName(), e);
        }
    }

    /** Phải gọi trong một transaction để thao tác xóa + chèn là nguyên tử. */
    public LoadResult load(TableSpec spec, List<Map<String, String>> rows) {
        checkHeader(spec, rows);
        References refs = new References(
                ids("select ticker from bank"),
                ids("select code from indicator"),
                ids("select code from policy_program"));

        List<Object[]> values = new ArrayList<>(rows.size());
        int skipped = 0;
        for (int i = 0; i < rows.size(); i++) {
            Object[] converted = convert(spec, rows.get(i), i + 2, refs); // +2: dòng 1 là tiêu đề
            if (converted == null) {
                skipped++;
            } else {
                values.add(converted);
            }
        }
        return switch (spec.mode()) {
            case REPLACE -> replace(spec, values, skipped);
            case UPSERT -> upsert(spec, values, skipped);
        };
    }

    /** Giá trị lớn nhất của cột mốc (ví dụ ngày lãi suất mới nhất), dạng chuỗi; null nếu bảng rỗng. */
    public String marker(TableSpec spec) {
        if (spec.markerColumn() == null) {
            return null;
        }
        Object value = jdbc.queryForObject(
                "select max(" + spec.markerColumn() + ") from " + spec.table(), Object.class);
        return value == null ? null : value.toString();
    }

    public long count(String table) {
        Long count = jdbc.queryForObject("select count(*) from " + table, Long.class);
        return count == null ? 0 : count;
    }

    private LoadResult replace(TableSpec spec, List<Object[]> values, int skipped) {
        jdbc.update("delete from " + spec.table());
        String columns = spec.columns().stream().map(TableSpec.ColumnSpec::db).collect(Collectors.joining(", "));
        String params = spec.columns().stream().map(c -> "?").collect(Collectors.joining(", "));
        String sql = "insert into " + spec.table() + " (" + columns + ") values (" + params + ")";
        for (int from = 0; from < values.size(); from += BATCH_SIZE) {
            jdbc.batchUpdate(sql, values.subList(from, Math.min(from + BATCH_SIZE, values.size())));
        }
        return new LoadResult(values.size(), skipped);
    }

    /** Bảng tham chiếu có khóa ngoại trỏ tới, nên cập nhật theo khóa thay vì xóa rồi chèn. */
    private LoadResult upsert(TableSpec spec, List<Object[]> values, int skipped) {
        List<TableSpec.ColumnSpec> columns = spec.columns();
        List<Integer> keyIdx = new ArrayList<>();
        List<Integer> valueIdx = new ArrayList<>();
        for (int i = 0; i < columns.size(); i++) {
            (spec.keyColumns().contains(columns.get(i).db()) ? keyIdx : valueIdx).add(i);
        }
        String update = "update " + spec.table() + " set "
                + valueIdx.stream().map(i -> columns.get(i).db() + " = ?").collect(Collectors.joining(", "))
                + " where " + keyIdx.stream().map(i -> columns.get(i).db() + " = ?").collect(Collectors.joining(" and "));
        String insert = "insert into " + spec.table() + " ("
                + columns.stream().map(TableSpec.ColumnSpec::db).collect(Collectors.joining(", ")) + ") values ("
                + columns.stream().map(c -> "?").collect(Collectors.joining(", ")) + ")";
        for (Object[] row : values) {
            Object[] args = new Object[columns.size()];
            int j = 0;
            for (int i : valueIdx) {
                args[j++] = row[i];
            }
            for (int i : keyIdx) {
                args[j++] = row[i];
            }
            if (jdbc.update(update, args) == 0) {
                jdbc.update(insert, row);
            }
        }
        return new LoadResult(values.size(), skipped);
    }

    private static void checkHeader(TableSpec spec, List<Map<String, String>> rows) {
        if (rows.isEmpty()) {
            return;
        }
        Set<String> header = rows.getFirst().keySet();
        List<String> missing = spec.columns().stream()
                .filter(TableSpec.ColumnSpec::required)
                .map(TableSpec.ColumnSpec::csv)
                .filter(name -> !header.contains(name))
                .toList();
        if (!missing.isEmpty()) {
            throw new ImportValidationException(spec.fileName() + " thiếu cột bắt buộc: " + String.join(", ", missing));
        }
    }

    /** Trả null nếu dòng bị bỏ qua (mã tham chiếu lạ); ném lỗi nếu dữ liệu sai kiểu hoặc thiếu ô bắt buộc. */
    private static Object[] convert(TableSpec spec, Map<String, String> row, int line, References refs) {
        Object[] values = new Object[spec.columns().size()];
        for (int i = 0; i < values.length; i++) {
            TableSpec.ColumnSpec column = spec.columns().get(i);
            String raw = row.get(column.csv());
            String text = raw == null ? null : raw.strip();
            if (text == null || text.isEmpty()) {
                if (column.required()) {
                    throw new ImportValidationException(
                            spec.fileName() + " dòng " + line + ": cột " + column.csv() + " bị trống");
                }
                values[i] = null;
                continue;
            }
            try {
                Object value = parse(column.type(), text);
                if (!refs.accepts(column.type(), text)) {
                    return null;
                }
                values[i] = value;
            } catch (RuntimeException e) {
                throw new ImportValidationException(spec.fileName() + " dòng " + line + ": cột " + column.csv()
                        + " không đọc được giá trị '" + text + "'");
            }
        }
        return values;
    }

    static Object parse(ColumnType type, String text) {
        return switch (type) {
            case TEXT, TICKER, INDICATOR, PROGRAM -> text;
            // pandas ghi số nguyên thành "3.0" khi cột có ô trống, nên đọc qua BigDecimal.
            case INT -> new BigDecimal(text).intValueExact();
            case LONG -> new BigDecimal(text).longValueExact();
            case DOUBLE -> Double.parseDouble(text);
            case DECIMAL -> new BigDecimal(text);
            case DATE -> Date.valueOf(LocalDate.parse(text.length() > 10 ? text.substring(0, 10) : text));
            case BOOL -> switch (text.toLowerCase()) {
                case "1", "1.0", "true" -> true;
                case "0", "0.0", "false" -> false;
                default -> throw new IllegalArgumentException(text);
            };
        };
    }

    private Set<String> ids(String sql) {
        return new HashSet<>(jdbc.queryForList(sql, String.class));
    }

    private record References(Set<String> tickers, Set<String> indicators, Set<String> programs) {

        boolean accepts(ColumnType type, String value) {
            return switch (type) {
                case TICKER -> tickers.contains(value);
                case INDICATOR -> indicators.contains(value);
                case PROGRAM -> programs.contains(value);
                default -> true;
            };
        }
    }
}
