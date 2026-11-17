package vn.kltn.bankadvisor.security;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.security.web.csrf.CsrfToken;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;

/**
 * Spring Security chỉ tạo token CSRF khi có code đọc nó. Giao diện (SPA) cần cookie XSRF-TOKEN có sẵn trước request
 * đổi trạng thái đầu tiên, nên filter này đọc token ở mọi request: cookie chưa có thì được cấp, có rồi thì giữ nguyên.
 */
class CsrfCookieFilter extends OncePerRequestFilter {

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain chain)
            throws ServletException, IOException {
        if (request.getAttribute(CsrfToken.class.getName()) instanceof CsrfToken token) {
            token.getToken();
        }
        chain.doFilter(request, response);
    }
}
