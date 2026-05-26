import { useEffect, useState } from "react";
import { Monitor } from "lucide-react";

const MOBILE_BREAKPOINT = 768;

export default function MobileGuard({ children }: { children: React.ReactNode }) {
  const [isMobile, setIsMobile] = useState(
    () => window.innerWidth < MOBILE_BREAKPOINT
  );

  useEffect(() => {
    const mq = window.matchMedia(`(max-width: ${MOBILE_BREAKPOINT - 1}px)`);
    const handler = (e: MediaQueryListEvent) => setIsMobile(e.matches);
    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  }, []);

  if (!isMobile) return <>{children}</>;

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-8">
      <div className="max-w-sm text-center space-y-6">
        <div className="flex justify-center">
          <div className="rounded-full bg-primary/10 p-5">
            <Monitor className="w-12 h-12 text-primary" />
          </div>
        </div>
        <div className="space-y-2">
          <h1 className="text-2xl font-semibold text-foreground">
            Desktop Required
          </h1>
          <p className="text-muted-foreground leading-relaxed">
            MedFabric is designed for desktop use. Please visit on a larger
            screen for the best experience.
          </p>
        </div>
      </div>
    </div>
  );
}
