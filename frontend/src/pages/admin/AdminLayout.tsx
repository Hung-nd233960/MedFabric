import { NavLink, Outlet } from "react-router-dom";
import {
  Users,
  Database,
  UserSquare2,
  ImageIcon,
  Link2,
  Download,
  ArrowLeft,
} from "lucide-react";
import { cn } from "@/lib/utils";
import ThemeToggle from "@/components/layout/ThemeToggle";
import { Link } from "react-router-dom";

const NAV_ITEMS = [
  { to: "doctors", label: "Doctors", icon: Users },
  { to: "datasets", label: "Datasets", icon: Database },
  { to: "patients", label: "Patients", icon: UserSquare2 },
  { to: "image-sets", label: "Image Sets", icon: ImageIcon },
  { to: "assignments", label: "Assignments", icon: Link2 },
  { to: "export", label: "Export", icon: Download },
];

export default function AdminLayout() {
  return (
    <div className="min-h-screen flex bg-background">
      {/* Sidebar */}
      <aside className="w-52 border-r flex flex-col">
        <div className="p-4 border-b flex items-center justify-between">
          <div>
            <div className="font-bold text-sm text-primary">MedFabric</div>
            <div className="text-[10px] text-muted-foreground">Admin Panel</div>
          </div>
          <ThemeToggle />
        </div>
        <nav className="flex-1 p-2 space-y-1">
          {NAV_ITEMS.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-2.5 rounded-md px-3 py-2 text-sm transition-colors",
                  isActive
                    ? "bg-primary/10 text-primary font-medium"
                    : "text-muted-foreground hover:bg-muted hover:text-foreground"
                )
              }
            >
              <Icon className="h-4 w-4 shrink-0" />
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="p-2 border-t">
          <Link
            to="/"
            className="flex items-center gap-2 px-3 py-2 rounded-md text-sm text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to App
          </Link>
        </div>
      </aside>

      {/* Main */}
      <main className="flex-1 overflow-auto">
        <Outlet />
      </main>
    </div>
  );
}
