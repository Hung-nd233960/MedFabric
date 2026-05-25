import { Link, useNavigate } from "react-router-dom";
import { LogOut, Settings, LayoutDashboard } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import ThemeToggle from "./ThemeToggle";
import { useAuthStore } from "@/store/authStore";
import { authApi } from "@/lib/api";

export default function Navbar() {
  const { role, logout } = useAuthStore();
  const navigate = useNavigate();

  const handleLogout = async () => {
    try {
      await authApi.logout();
    } finally {
      logout();
      navigate("/login");
    }
  };

  return (
    <header className="sticky top-0 z-40 border-b bg-background/95 backdrop-blur">
      <div className="flex h-12 items-center gap-3 px-4">
        <Link to="/" className="flex items-center gap-2 font-semibold text-sm">
          <span className="text-primary font-bold text-base">MedFabric</span>
          <span className="text-muted-foreground text-xs">3.0</span>
        </Link>

        <Separator orientation="vertical" className="h-5" />

        <Link to="/">
          <Button variant="ghost" size="sm" className="gap-1.5">
            <LayoutDashboard className="h-4 w-4" />
            Dashboard
          </Button>
        </Link>

        {role === "Admin" && (
          <Link to="/admin">
            <Button variant="ghost" size="sm" className="gap-1.5">
              <Settings className="h-4 w-4" />
              Admin
            </Button>
          </Link>
        )}

        <div className="ml-auto flex items-center gap-1">
          <ThemeToggle />
          <Button variant="ghost" size="icon" onClick={handleLogout} title="Log out">
            <LogOut className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </header>
  );
}
