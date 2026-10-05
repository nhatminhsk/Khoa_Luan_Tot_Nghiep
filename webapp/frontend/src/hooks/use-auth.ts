"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { queryKeys } from "@/lib/query/keys";
import { authRepository, type LoginInput, type RegisterInput } from "@/repositories/auth.repository";

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
  const logout = useMutation({
    mutationFn: authRepository.logout,
    onSuccess: () => {
      queryClient.setQueryData(queryKeys.me, null);
      queryClient.removeQueries({ queryKey: ["me"] });
      queryClient.removeQueries({ queryKey: ["admin"] });
    },
  });

  const user = me.data ?? null;
  return {
    user,
    isLoading: me.isLoading,
    isAuthenticated: user !== null,
    isAdmin: user?.role === "ADMIN",
    login,
    register,
    logout,
  };
}
