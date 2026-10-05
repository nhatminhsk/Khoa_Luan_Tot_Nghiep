package vn.kltn.bankadvisor.module.user.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import vn.kltn.bankadvisor.module.user.entity.AppUser;

import java.util.List;
import java.util.Optional;

public interface AppUserRepository extends JpaRepository<AppUser, Long> {

    Optional<AppUser> findByEmail(String email);

    boolean existsByEmail(String email);

    List<AppUser> findByNotifyNewRankingTrue();
}
