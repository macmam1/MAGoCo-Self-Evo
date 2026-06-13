import { Link } from "react-router-dom";

export default function ForbiddenPage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-900 to-slate-800 p-4">
      <div className="text-center">
        <h1 className="text-6xl font-bold text-red-500 mb-4">403</h1>
        <p className="text-xl text-slate-300 mb-6">دسترسی غیرمجاز</p>
        <Link
          to="/"
          className="inline-block px-6 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg text-white transition"
        >
          بازگشت به خانه
        </Link>
      </div>
    </div>
  );
}
