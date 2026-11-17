import { z } from "zod";

/** Quy tắc mật khẩu mới, giống RegisterRequest / ChangePasswordRequest bên backend (backend vẫn kiểm tra lại). */
export const newPasswordSchema = z
  .string()
  .min(8, "Mật khẩu dài 8–72 ký tự")
  .max(72, "Mật khẩu dài 8–72 ký tự")
  .regex(/^(?=.*\p{L})(?=.*\d).+$/u, "Mật khẩu cần có cả chữ và số");
