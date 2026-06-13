import { useEffect } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { useAuthStore } from "@/stores/authStore";

interface ProtectedRouteProps {
  children: React.ReactNode;
  requireRole?: "admin" | "user" | "viewer";
}

export function ProtectedRoute({ children, requireRole }: ProtectedRouteProps) {
  const { isAuthenticated, user, fetchMe, accessToken } = useAuthStore();
  const location = useLocation();

  useEffect(() => {
    if (accessToken && !user) {
      void fetchMe();
    }
  }, [accessToken, user, fetchMe]);

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  if (requireRole && user && user.role !== requireRole && user.role !== "admin") {
    return <Navigate to="/forbidden" replace />;
  }

  return <>{children}</>;
}

export default ProtectedRoute;
