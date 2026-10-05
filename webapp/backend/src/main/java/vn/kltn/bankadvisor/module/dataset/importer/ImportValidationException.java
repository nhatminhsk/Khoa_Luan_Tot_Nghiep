package vn.kltn.bankadvisor.module.dataset.importer;

/** File CSV sai hợp đồng dữ liệu (thiếu cột, sai kiểu, ô bắt buộc trống). Cả tập bị từ chối, bảng giữ nguyên. */
public class ImportValidationException extends RuntimeException {

    public ImportValidationException(String message) {
        super(message);
    }
}
