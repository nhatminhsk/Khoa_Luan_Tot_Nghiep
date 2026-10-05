package vn.kltn.bankadvisor.module.need.service;

import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import vn.kltn.bankadvisor.common.exception.AppException;
import vn.kltn.bankadvisor.common.exception.ErrorCode;
import vn.kltn.bankadvisor.module.need.dto.SavedNeedRequest;
import vn.kltn.bankadvisor.module.need.dto.SavedNeedResponse;
import vn.kltn.bankadvisor.module.need.entity.SavedNeed;
import vn.kltn.bankadvisor.module.need.repository.SavedNeedRepository;

import java.time.Clock;
import java.util.List;

@Service
@Transactional
public class SavedNeedService {

    static final int MAX_NEEDS_PER_USER = 20;

    private final SavedNeedRepository repository;
    private final Clock clock;

    public SavedNeedService(SavedNeedRepository repository, Clock clock) {
        this.repository = repository;
        this.clock = clock;
    }

    @Transactional(readOnly = true)
    public List<SavedNeedResponse> list(long userId) {
        return repository.findByUserIdOrderByUpdatedAtDesc(userId).stream().map(SavedNeedResponse::from).toList();
    }

    public SavedNeedResponse create(long userId, SavedNeedRequest request) {
        if (repository.countByUserId(userId) >= MAX_NEEDS_PER_USER) {
            throw new AppException(ErrorCode.BAD_REQUEST, "Mỗi tài khoản lưu tối đa " + MAX_NEEDS_PER_USER + " nhu cầu");
        }
        SavedNeed need = SavedNeed.create(userId, clock.instant());
        apply(need, request);
        return SavedNeedResponse.from(repository.save(need));
    }

    public SavedNeedResponse update(long userId, long id, SavedNeedRequest request) {
        SavedNeed need = owned(userId, id);
        apply(need, request);
        return SavedNeedResponse.from(need);
    }

    public void delete(long userId, long id) {
        repository.delete(owned(userId, id));
    }

    /** Chỉ chủ sở hữu mới thấy nhu cầu của mình; id của người khác trả NOT_FOUND (không lộ là có tồn tại). */
    private SavedNeed owned(long userId, long id) {
        return repository.findByIdAndUserId(id, userId).orElseThrow(() -> new AppException(ErrorCode.NOT_FOUND));
    }

    private void apply(SavedNeed need, SavedNeedRequest r) {
        need.apply(r.purpose(), r.label().strip(), r.amount(), r.termMonths(), r.channel(), r.loanPurpose(),
                r.repayment(), r.weightRate(), r.weightSafety(), r.weightApp(), clock.instant());
    }
}
