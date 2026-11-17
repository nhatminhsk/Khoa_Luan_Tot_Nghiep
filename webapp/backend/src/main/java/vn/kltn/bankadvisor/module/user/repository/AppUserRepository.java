package vn.kltn.bankadvisor.module.user.repository;

import jakarta.persistence.LockModeType;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.JpaSpecificationExecutor;
import org.springframework.data.jpa.repository.Lock;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import vn.kltn.bankadvisor.module.user.entity.AppUser;
import vn.kltn.bankadvisor.module.user.entity.Role;
import vn.kltn.bankadvisor.module.user.entity.UserStatus;

import java.util.List;
import java.util.Optional;

public interface AppUserRepository extends JpaRepository<AppUser, Long>, JpaSpecificationExecutor<AppUser> {

    Optional<AppUser> findByEmail(String email);

    boolean existsByEmail(String email);

    List<AppUser> findByNotifyNewRankingTrue();

    long countByStatus(UserStatus status);

    long countByRole(Role role);

    long countByEmailVerifiedAtIsNotNull();

    /**
     * Khóa hàng (SELECT … FOR UPDATE) các quản trị viên đang hoạt động trước khi khóa / hạ quyền một quản trị viên:
     * hai thao tác chạy cùng lúc không thể cùng vượt kiểm tra "còn ít nhất một quản trị viên".
     */
    @Lock(LockModeType.PESSIMISTIC_WRITE)
    @Query("select u from AppUser u where u.role = :role and u.status = :status")
    List<AppUser> lockByRoleAndStatus(@Param("role") Role role, @Param("status") UserStatus status);
}
