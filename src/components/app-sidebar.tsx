import { Link, useRouterState } from "@tanstack/react-router";
import { LayoutDashboard, Sparkles, Send, Settings } from "lucide-react";
import { useEffect, useState } from "react";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar";
import { pingBackend, API_BASE_URL } from "@/lib/api";
import { cn } from "@/lib/utils";

const items = [
  { title: "대시보드", url: "/", icon: LayoutDashboard },
  { title: "콘텐츠 생성", url: "/create", icon: Sparkles },
  { title: "배포 관리", url: "/publish", icon: Send },
  { title: "세팅", url: "/settings", icon: Settings },
] as const;

export function AppSidebar() {
  const pathname = useRouterState({ select: (r) => r.location.pathname });
  const [online, setOnline] = useState<boolean | null>(null);

  useEffect(() => {
    let cancelled = false;
    const check = async () => {
      const ok = await pingBackend();
      if (!cancelled) setOnline(ok);
    };
    check();
    const id = setInterval(check, 15000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  return (
    <Sidebar collapsible="icon">
      <SidebarHeader className="border-b px-4 py-4">
        <div className="flex items-center gap-2">
          <div className="h-8 w-8 rounded-md bg-primary text-primary-foreground grid place-items-center font-bold">
            M
          </div>
          <div className="flex flex-col">
            <span className="text-sm font-semibold">Marketing Auto</span>
            <span className="text-xs text-muted-foreground">1인 자동화</span>
          </div>
        </div>
      </SidebarHeader>
      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel>Workflow</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {items.map((item) => {
                const active =
                  item.url === "/"
                    ? pathname === "/"
                    : pathname.startsWith(item.url);
                return (
                  <SidebarMenuItem key={item.url}>
                    <SidebarMenuButton asChild isActive={active}>
                      <Link to={item.url} className="flex items-center gap-2">
                        <item.icon className="h-4 w-4" />
                        <span>{item.title}</span>
                      </Link>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                );
              })}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>
      <SidebarFooter className="border-t px-4 py-3">
        <div className="flex items-center gap-2 text-xs">
          <span
            className={cn(
              "h-2 w-2 rounded-full",
              online === null && "bg-muted-foreground animate-pulse",
              online === true && "bg-emerald-500",
              online === false && "bg-destructive",
            )}
          />
          <span className="text-muted-foreground truncate">
            {API_BASE_URL.replace(/^https?:\/\//, "")}
          </span>
        </div>
      </SidebarFooter>
    </Sidebar>
  );
}
