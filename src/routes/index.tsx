import { createFileRoute, Link } from "@tanstack/react-router";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import {
  Sparkles,
  CheckCircle2,
  XCircle,
  Clock,
  ArrowRight,
  Trash2,
} from "lucide-react";
import { toast } from "sonner";
import { listContent, deleteContent, type GeneratedContent, type Platform } from "@/lib/api";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "대시보드 · beconti" },
      { name: "description", content: "생성 및 배포 상태 요약 대시보드" },
    ],
  }),
  component: Dashboard,
});

const PLATFORMS: Platform[] = ["naver_blog", "naver_clip", "instagram"];

function Dashboard() {
  const qc = useQueryClient();
  const { data: content = [], isError } = useQuery({
    queryKey: ["content"],
    queryFn: listContent,
    refetchInterval: 10000,
  });
  const deleteMut = useMutation({
    mutationFn: (id: string) => deleteContent(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["content"] });
      toast.success("삭제했습니다");
    },
    onError: (e: Error) => toast.error("삭제 실패", { description: e.message }),
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
                <li key={c.id} className="py-3 flex items-center gap-3 group">
                  <Link
                    to="/content/$id"
                    params={{ id: c.id }}
                    className="flex-1 flex items-center justify-between gap-4 min-w-0 hover:bg-muted/40 rounded-md px-2 -mx-2 py-1"
                  >
                    <div className="min-w-0">
                      <p className="font-medium truncate">{c.title || "(제목 없음)"}</p>
                      <p className="text-xs text-muted-foreground">
                        {new Date(c.createdAt).toLocaleString("ko-KR")}
                      </p>
                    </div>
                    <div className="flex gap-1 shrink-0">
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
                  </Link>
                  <AlertDialog>
                    <AlertDialogTrigger asChild>
                      <button
                        type="button"
                        title="삭제"
                        className="h-8 w-8 grid place-items-center rounded-md text-muted-foreground hover:text-destructive hover:bg-destructive/10 opacity-0 group-hover:opacity-100 transition"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </AlertDialogTrigger>
                    <AlertDialogContent>
                      <AlertDialogHeader>
                        <AlertDialogTitle>이 콘텐츠를 삭제할까요?</AlertDialogTitle>
                        <AlertDialogDescription>
                          "{c.title || "(제목 없음)"}" 및 생성된 숏폼 영상이 삭제됩니다. 되돌릴 수 없습니다.
                        </AlertDialogDescription>
                      </AlertDialogHeader>
                      <AlertDialogFooter>
                        <AlertDialogCancel>취소</AlertDialogCancel>
                        <AlertDialogAction
                          onClick={() => deleteMut.mutate(c.id)}
                          className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                        >
                          삭제
                        </AlertDialogAction>
                      </AlertDialogFooter>
                    </AlertDialogContent>
                  </AlertDialog>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
