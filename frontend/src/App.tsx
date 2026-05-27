import { Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from "sonner";
import { useAuthStore } from "@/store/authStore";
import MobileGuard from "@/components/MobileGuard";
import { TooltipProvider } from "@/components/ui/tooltip";
import AppLayout from "@/components/layout/AppLayout";
import LoginPage from "@/pages/LoginPage";
import RegisterPage from "@/pages/RegisterPage";
import DashboardPage from "@/pages/DashboardPage";
import LabelPage from "@/pages/LabelPage";
import AdminLayout from "@/pages/admin/AdminLayout";
import DoctorsPage from "@/pages/admin/DoctorsPage";
import DatasetsPage from "@/pages/admin/DatasetsPage";
import PatientsPage from "@/pages/admin/PatientsPage";
import ImageSetsPage from "@/pages/admin/ImageSetsPage";
import AssignmentsPage from "@/pages/admin/AssignmentsPage";
import ExportPage from "@/pages/admin/ExportPage";
import SubmissionsPage from "@/pages/admin/SubmissionsPage";
import ChangePasswordPage from "@/pages/ChangePasswordPage";

function RequireAuth({ children }: { children: React.ReactNode }) {
  const token = useAuthStore((s) => s.accessToken);
  if (!token) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

function RequireAdmin({ children }: { children: React.ReactNode }) {
  const role = useAuthStore((s) => s.role);
  const token = useAuthStore((s) => s.accessToken);
  if (!token) return <Navigate to="/login" replace />;
  if (role !== "Admin") return <Navigate to="/" replace />;
  return <>{children}</>;
}

export default function App() {
  return (
    <MobileGuard>
      <TooltipProvider delayDuration={300}>
      <Toaster richColors position="top-right" />
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />

        <Route
          element={
            <RequireAuth>
              <AppLayout />
            </RequireAuth>
          }
        >
          <Route path="/" element={<DashboardPage />} />
          <Route path="/change-password" element={<ChangePasswordPage />} />
          <Route path="/label" element={<LabelPage />} />
        </Route>

        <Route
          path="/admin"
          element={
            <RequireAdmin>
              <AdminLayout />
            </RequireAdmin>
          }
        >
          <Route index element={<Navigate to="doctors" replace />} />
          <Route path="doctors" element={<DoctorsPage />} />
          <Route path="datasets" element={<DatasetsPage />} />
          <Route path="patients" element={<PatientsPage />} />
          <Route path="image-sets" element={<ImageSetsPage />} />
          <Route path="assignments" element={<AssignmentsPage />} />
          <Route path="submissions" element={<SubmissionsPage />} />
          <Route path="export" element={<ExportPage />} />
        </Route>

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
      </TooltipProvider>
    </MobileGuard>
  );
}
