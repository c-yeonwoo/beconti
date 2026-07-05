import { createFileRoute, Link } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Sparkles,
  CheckCircle2,
  XCircle,
  Clock,
  ArrowRight,
} from "lucide-react";
import { listContent, type GeneratedContent, type Platform } from "@/lib/api";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "대시보드 · beconti" },
      { name: "description", content: "생성 및 배포 상태 요약 대시보드" },
    ],
  }),
  component: Dashboard,
});

const PLATFORMS: Platform[] = ["naver_blog", "naver_clip", "wordpress", "instagram"];

function Dashboard() {
  const { data: content = [], isError } = useQuery({
    queryKey: ["content"],
    queryFn: listContent,
    refetchInterval: 10000,
  });

  let success = 0,
    failed = 0,
    queued = 0;
  for (const c of content) {
    for (const p of PLATFORMS) {
      const s = c.platformStatus[p];
      if (s === "success") success++;
      else if (s === "failed") failed++;
      else if (s === "queued") queued++;
    }
  }

  const stats = [
    { label: "총 생성 콘텐츠", value: content.length, icon: Sparkles, color: "text-primary" },
    { label: "배포 성공", value: success, icon: CheckCircle2, color: "text-emerald-500" },
    { label: "배포 실패", value: failed, icon: XCircle, color: "text-destructive" },
    { label: "대기 중", value: queued, icon: Clock, color: "text-amber-500" },
  ];

  const recent = content.slice(0, 5);

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">대시보드</h1>
          <p className="text-sm text-muted-foreground">
            콘텐츠 파이프라인 상태를 한눈에 확인하세요.
          </p>
        </div>
        <Button asChild>
          <Link to="/create">
            <Sparkles className="h-4 w-4" /> 새 콘텐츠
          </Link>
        </Button>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {stats.map((s) => (
          <Card key={s.label}>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                {s.label}
              </CardTitle>
              <s.icon className={`h-4 w-4 ${s.color}`} />
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-semibold">{s.value}</div>
            </CardContent>
          </Card>
        ))}
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">최근 콘텐츠</CardTitle>
        </CardHeader>
        <CardContent>
          {isError ? (
            <div className="py-12 text-center text-sm text-destructive">
              백엔드(localhost:8000) 연결 실패
            </div>
          ) : recent.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 text-center">
              <div className="rounded-full bg-muted p-4">
                <Sparkles className="h-6 w-6 text-muted-foreground" />
              </div>
              <p className="mt-4 text-sm text-muted-foreground">
                아직 생성된 콘텐츠가 없습니다.
              </p>
              <Button asChild variant="outline" className="mt-4">
                <Link to="/create">
                  콘텐츠 생성 시작 <ArrowRight className="h-4 w-4" />
                </Link>
              </Button>
              <Badge variant="secondary" className="mt-3">
                백엔드 연결 시 자동으로 채워집니다
              </Badge>
            </div>
          ) : (
            <ul className="divide-y">
              {recent.map((c: GeneratedContent) => (
                <li key={c.id} className="py-3 flex items-center justify-between gap-4">
                  <div className="min-w-0">
                    <p className="font-medium truncate">{c.title || "(제목 없음)"}</p>
                    <p className="text-xs text-muted-foreground">
                      {new Date(c.createdAt).toLocaleString("ko-KR")}
                    </p>
                  </div>
                  <div className="flex gap-1">
                    {PLATFORMS.map((p) => {
                      const s = c.platformStatus[p];
                      const color =
                        s === "success"
                          ? "bg-emerald-500"
                          : s === "failed"
                            ? "bg-destructive"
                            : s === "queued"
                              ? "bg-amber-500"
                              : "bg-muted";
                      return <span key={p} className={`h-2 w-2 rounded-full ${color}`} title={`${p}: ${s}`} />;
                    })}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
