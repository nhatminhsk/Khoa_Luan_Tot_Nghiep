package vn.kltn.bankadvisor.module.dataset.controller;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import vn.kltn.bankadvisor.common.api.ApiResponse;
import vn.kltn.bankadvisor.module.dataset.dto.DatasetsResponse;
import vn.kltn.bankadvisor.module.dataset.service.DatasetService;

@RestController
@RequestMapping("/api/v1/datasets")
public class DatasetController {

    private final DatasetService datasetService;

    public DatasetController(DatasetService datasetService) {
        this.datasetService = datasetService;
    }

    /** Nguồn dữ liệu, ngày cập nhật, độ phủ và trạng thái kết quả thuật toán. */
    @GetMapping
    public ApiResponse<DatasetsResponse> overview() {
        return ApiResponse.ok(datasetService.overview());
    }
}
