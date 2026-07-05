import { createFileRoute, Link } from "@tanstack/react-router";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Sparkles, CheckCircle2, XCircle, Clock, ArrowRight } from "lucide-react";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "대시보드 · beconti" },
      { name: "description", content: "생성 및 배포 상태 요약 대시보드" },
    ],
  }),
  component: Dashboard,
});

const stats = [
  { label: "총 생성 콘텐츠", value: 0, icon: Sparkles, color: "text-primary" },
  { label: "배포 성공", value: 0, icon: CheckCircle2, color: "text-emerald-500" },
  { label: "배포 실패", value: 0, icon: XCircle, color: "text-destructive" },
  { label: "대기 중", value: 0, icon: Clock, color: "text-amber-500" },
];

function Dashboard() {
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
        </CardContent>
      </Card>
    </div>
  );
}
