"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { queryKeys } from "@/lib/query/keys";
import { authRepository, type LoginInput, type RegisterInput } from "@/repositories/auth.repository";
import type { Permission } from "@/types/api";

/** Trạng thái đăng nhập dùng chung cho mọi component (một request /auth/me, cache lại). */
export function useAuth() {
  const queryClient = useQueryClient();
  const me = useQuery({ queryKey: queryKeys.me, queryFn: authRepository.me, staleTime: 10 * 60 * 1000 });

  const onSession = (user: Awaited<ReturnType<typeof authRepository.login>>) => {
    queryClient.setQueryData(queryKeys.me, user);
    // Dữ liệu cá nhân của phiên trước (nếu có) không còn đúng.
    queryClient.removeQueries({ queryKey: ["me"] });
  };

  const login = useMutation({ mutationFn: (input: LoginInput) => authRepository.login(input), onSuccess: onSession });
  const register = useMutation({
    mutationFn: (input: RegisterInput) => authRepository.register(input),
    onSuccess: onSession,
  });
  const clearSession = () => {
    queryClient.setQueryData(queryKeys.me, null);
    queryClient.removeQueries({ queryKey: ["me"] });
    queryClient.removeQueries({ queryKey: ["admin"] });
  };
  const logout = useMutation({ mutationFn: authRepository.logout, onSuccess: clearSession });
  const logoutEverywhere = useMutation({ mutationFn: authRepository.revokeAllSessions, onSuccess: clearSession });

  const user = me.data ?? null;
  /** Có quyền theo chức năng không — chỉ để dựng giao diện; quyền thật do backend kiểm. */
  const can = (permission: Permission) => user?.permissions?.includes(permission) ?? false;
  return {
    user,
    isLoading: me.isLoading,
    isAuthenticated: user !== null,
    isAdmin: user?.role === "ADMIN",
    can,
    login,
    register,
    logout,
    logoutEverywhere,
  };
}
