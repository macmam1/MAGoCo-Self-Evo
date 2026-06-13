import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import toast from "react-hot-toast";
import { useAuthStore } from "@/stores/authStore";

const registerSchema = z
  .object({
    email: z.string().email("ایمیل نامعتبر"),
    username: z
      .string()
      .min(3, "حداقل ۳ کاراکتر")
      .max(50)
      .regex(/^[a-zA-Z0-9_-]+$/, "فقط حروف انگلیسی، اعداد، - و _"),
    full_name: z.string().optional(),
    password: z.string().min(8, "حداقل ۸ کاراکتر"),
    confirm_password: z.string(),
  })
  .refine((data) => data.password === data.confirm_password, {
    message: "رمزها یکسان نیستند",
    path: ["confirm_password"],
  });

type RegisterForm = z.infer<typeof registerSchema>;

export default function RegisterPage() {
  const navigate = useNavigate();
  const { register: registerUser, isLoading, error, clearError } = useAuthStore();
  const [localError, setLocalError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<RegisterForm>({
    resolver: zodResolver(registerSchema),
  });

  const onSubmit = async (data: RegisterForm) => {
    setLocalError(null);
    clearError();
    try {
      await registerUser({
        email: data.email,
        username: data.username,
        password: data.password,
        full_name: data.full_name,
      });
      toast.success("ثبت‌نام موفقیت‌آمیز");
      navigate("/");
    } catch (err: unknown) {
      const message =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        "خطا در ثبت‌نام";
      setLocalError(message);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-900 to-slate-800 p-4">
      <div className="w-full max-w-md bg-slate-800/70 backdrop-blur rounded-2xl p-8 border border-slate-700">
        <h1 className="text-3xl font-bold text-white mb-2 text-center">ثبت‌نام</h1>
        <p className="text-slate-400 text-center mb-6">ساخت حساب جدید</p>

        {(error || localError) && (
          <div className="mb-4 p-3 bg-red-500/20 border border-red-500 rounded-lg text-red-200 text-sm">
            {localError || error}
          </div>
        )}

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div>
            <label className="block text-slate-300 text-sm mb-1">ایمیل</label>
            <input
              {...register("email")}
              type="email"
              className="w-full px-4 py-2 bg-slate-900 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-blue-500"
              autoComplete="email"
            />
            {errors.email && <p className="text-red-400 text-xs mt-1">{errors.email.message}</p>}
          </div>

          <div>
            <label className="block text-slate-300 text-sm mb-1">نام کاربری</label>
            <input
              {...register("username")}
              type="text"
              className="w-full px-4 py-2 bg-slate-900 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-blue-500"
              autoComplete="username"
            />
            {errors.username && (
              <p className="text-red-400 text-xs mt-1">{errors.username.message}</p>
            )}
          </div>

          <div>
            <label className="block text-slate-300 text-sm mb-1">نام کامل (اختیاری)</label>
            <input
              {...register("full_name")}
              type="text"
              className="w-full px-4 py-2 bg-slate-900 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-blue-500"
            />
          </div>

          <div>
            <label className="block text-slate-300 text-sm mb-1">رمز عبور</label>
            <input
              {...register("password")}
              type="password"
              className="w-full px-4 py-2 bg-slate-900 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-blue-500"
              autoComplete="new-password"
            />
            {errors.password && (
              <p className="text-red-400 text-xs mt-1">{errors.password.message}</p>
            )}
          </div>

          <div>
            <label className="block text-slate-300 text-sm mb-1">تکرار رمز عبور</label>
            <input
              {...register("confirm_password")}
              type="password"
              className="w-full px-4 py-2 bg-slate-900 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-blue-500"
              autoComplete="new-password"
            />
            {errors.confirm_password && (
              <p className="text-red-400 text-xs mt-1">{errors.confirm_password.message}</p>
            )}
          </div>

          <button
            type="submit"
            disabled={isLoading}
            className="w-full py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 rounded-lg text-white font-medium transition"
          >
            {isLoading ? "در حال ثبت‌نام..." : "ثبت‌نام"}
          </button>
        </form>

        <p className="text-slate-400 text-sm text-center mt-4">
          حساب دارید؟{" "}
          <Link to="/login" className="text-blue-400 hover:underline">
            ورود
          </Link>
        </p>
      </div>
    </div>
  );
}
