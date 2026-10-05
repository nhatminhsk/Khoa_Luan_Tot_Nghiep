package vn.kltn.bankadvisor.security;

import java.lang.annotation.ElementType;
import java.lang.annotation.Retention;
import java.lang.annotation.RetentionPolicy;
import java.lang.annotation.Target;

/**
 * Gắn vào tham số kiểu {@link AuthUser} của controller để nhận người dùng hiện tại.
 * Endpoint dùng annotation này phải nằm trong vùng yêu cầu đăng nhập của {@link SecurityConfig}.
 */
@Target(ElementType.PARAMETER)
@Retention(RetentionPolicy.RUNTIME)
public @interface CurrentUser {
}
