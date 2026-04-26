import { AppShell } from "@/components/app-shell";
import { DashboardDataProvider } from "@/hooks/useDashboardData";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <DashboardDataProvider>
      <AppShell>{children}</AppShell>
    </DashboardDataProvider>
  );
}
