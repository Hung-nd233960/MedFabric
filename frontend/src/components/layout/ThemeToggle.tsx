import { Moon, Sun } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useAppearanceStore } from "@/store/appearanceStore";

export default function ThemeToggle() {
  const { dark, setDark } = useAppearanceStore();

  return (
    <Button
      variant="ghost"
      size="icon"
      onClick={() => setDark(!dark)}
      title={dark ? "Switch to light mode" : "Switch to dark mode"}
    >
      {dark ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
    </Button>
  );
}
