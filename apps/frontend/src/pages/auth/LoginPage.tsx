import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import toast from "react-hot-toast";
import { useAuthStore } from "@/stores/authStore";

const loginSchema = z.object({
  username_or_email: z.string().min(1, "Required"),
  password: z.string().min(1, "Required"),
});

type LoginForm = z.infer<typeof loginSchema>;

export default function LoginPage() {
  const navigate = useNavigate();
  const { login, isLoading, error, clearError } = useAuthStore();
  const [localError, setLocalError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginForm>({
    resolver: zodResolver(loginSchema),
  });

  const onSubmit = async (data: LoginForm) => {
    setLocalError(null);
    clearError();
    try {
      await login(data);
      toast.success("ورود موفقیت‌آمیز");
      navigate("/");
    } catch (err: unknown) {
      const message =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        "خطا در ورود";
      setLocalError(message);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-900 to-slate-800 p-4">
      <div className="w-full max-w-md bg-slate-800/70 backdrop-blur rounded-2xl p-8 border border-slate-700">
        <h1 className="text-3xl font-bold text-white mb-2 text-center">ورود</h1>
        <p className="text-slate-400 text-center mb-6">به MAGoCo-Self-Evo خوش آمدید</p>

        {(error || localError) && (
          <div className="mb-4 p-3 bg-red-500/20 border border-red-500 rounded-lg text-red-200 text-sm">
            {localError || error}
          </div>
        )}

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div>
            <label className="block text-slate-300 text-sm mb-1">نام کاربری یا ایمیل</label>
            <input
              {...register("username_or_email")}
              type="text"
              className="w-full px-4 py-2 bg-slate-900 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-blue-500"
              autoComplete="username"
            />
            {errors.username_or_email && (
              <p className="text-red-400 text-xs mt-1">{errors.username_or_email.message}</p>
            )}
          </div>

          <div>
            <label className="block text-slate-300 text-sm mb-1">رمز عبور</label>
            <input
              {...register("password")}
              type="password"
              className="w-full px-4 py-2 bg-slate-900 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-blue-500"
              autoComplete="current-password"
            />
            {errors.password && (
              <p className="text-red-400 text-xs mt-1">{errors.password.message}</p>
            )}
          </div>

          <button
            type="submit"
            disabled={isLoading}
            className="w-full py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 rounded-lg text-white font-medium transition"
          >
            {isLoading ? "در حال ورود..." : "ورود"}
          </button>
        </form>

        <p className="text-slate-400 text-sm text-center mt-4">
          حساب ندارید؟{" "}
          <Link to="/register" className="text-blue-400 hover:underline">
            ثبت‌نام
          </Link>
        </p>
      </div>
    </div>
  );
}
