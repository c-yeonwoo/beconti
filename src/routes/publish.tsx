import { createFileRoute, Link } from "@tanstack/react-router";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
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
import { Loader2, RefreshCw, Send, Trash2 } from "lucide-react";
import { toast } from "sonner";
import {
  listContent,
  publishContent,
  deleteContent,
  type GeneratedContent,
  type Platform,
  type PublishStatus,
} from "@/lib/api";

export const Route = createFileRoute("/publish")({
  head: () => ({
    meta: [
      { title: "배포 관리 · beconti" },
      { name: "description", content: "플랫폼별 배포 상태 및 재시도" },
    ],
  }),
  component: PublishPage,
});

const platforms: { key: Platform; label: string }[] = [
  { key: "naver_blog", label: "네이버 블로그" },
  { key: "naver_clip", label: "네이버 클립" },
  { key: "instagram", label: "인스타그램" },
];

function PublishPage() {
  const qc = useQueryClient();
  const { data: rows = [], isLoading, isError, refetch, isFetching } = useQuery({
    queryKey: ["content"],
    queryFn: listContent,
    refetchInterval: 5000,
  });

  const publishMut = useMutation({
    mutationFn: (vars: { contentId: string; platforms: Platform[] }) =>
      publishContent(vars),
    onSuccess: (res, vars) => {
      qc.invalidateQueries({ queryKey: ["content"] });
      const labels = vars.platforms
        .map((k) => platforms.find((p) => p.key === k)?.label ?? k)
        .join(", ");
      toast[res.ok ? "success" : "error"](
        res.ok ? "발행 완료" : "발행 실패/대기",
        { description: labels },
      );
    },
    onError: (e: Error) =>
      toast.error("발행 요청 실패", { description: e.message }),
  });

  const deleteMut = useMutation({
    mutationFn: (contentId: string) => deleteContent(contentId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["content"] });
      toast.success("콘텐츠를 삭제했습니다");
    },
    onError: (e: Error) => toast.error("삭제 실패", { description: e.message }),
  });

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">배포 관리</h1>
          <p className="text-sm text-muted-foreground">
            최초 발행은 전체 플랫폼 일괄, 이후 재발행은 플랫폼별로 각각 진행합니다.
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={() => refetch()} disabled={isFetching}>
          <RefreshCw className={`h-4 w-4 ${isFetching ? "animate-spin" : ""}`} /> 새로고침
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">콘텐츠 큐</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="rounded-md border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>제목</TableHead>
                  <TableHead>생성일</TableHead>
                  {platforms.map((p) => (
                    <TableHead key={p.key}>{p.label}</TableHead>
                  ))}
                  <TableHead className="text-right">액션</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {isLoading ? (
                  <TableRow>
                    <TableCell colSpan={platforms.length + 3} className="text-center py-12">
                      <Loader2 className="h-4 w-4 animate-spin inline mr-2" />
                      불러오는 중...
                    </TableCell>
                  </TableRow>
                ) : isError ? (
                  <TableRow>
                    <TableCell colSpan={platforms.length + 3} className="text-center py-12 text-sm text-destructive">
                      백엔드(localhost:8000) 연결 실패. 서버가 실행 중인지 확인하세요.
                    </TableCell>
                  </TableRow>
                ) : rows.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={platforms.length + 3} className="text-center py-12 text-sm text-muted-foreground">
                      아직 배포 대기 중인 콘텐츠가 없습니다.
                    </TableCell>
                  </TableRow>
                ) : (
                  rows.map((row: GeneratedContent) => {
                    const allIdle = platforms.every(
                      (p) => row.platformStatus[p.key] === "idle",
                    );
                    const isPendingFor = (keys: Platform[]) =>
                      publishMut.isPending &&
                      publishMut.variables?.contentId === row.id &&
                      publishMut.variables.platforms.length === keys.length &&
                      publishMut.variables.platforms.every((k) => keys.includes(k));

                    return (
                      <TableRow key={row.id}>
                        <TableCell className="font-medium max-w-[280px] truncate">
                          <Link
                            to="/content/$id"
                            params={{ id: row.id }}
                            className="hover:underline text-primary"
                          >
                            {row.title || "(제목 없음)"}
                          </Link>
                        </TableCell>
                        <TableCell className="text-xs text-muted-foreground">
                          {new Date(row.createdAt).toLocaleString("ko-KR")}
                        </TableCell>
                        {platforms.map((p) => {
                          const status = row.platformStatus[p.key];
                          const pending = isPendingFor([p.key]);
                          return (
                            <TableCell key={p.key}>
                              <div className="flex items-center gap-1.5">
                                <StatusBadge status={status} />
                                <button
                                  type="button"
                                  disabled={publishMut.isPending}
                                  onClick={() =>
                                    publishMut.mutate({ contentId: row.id, platforms: [p.key] })
                                  }
                                  title={`${p.label} ${status === "idle" ? "발행" : "재발행"}`}
                                  className="h-6 w-6 grid place-items-center rounded-md text-muted-foreground hover:text-foreground hover:bg-muted disabled:opacity-40"
                                >
                                  {pending ? (
                                    <Loader2 className="h-3 w-3 animate-spin" />
                                  ) : (
                                    <RefreshCw className="h-3 w-3" />
                                  )}
                                </button>
                              </div>
                            </TableCell>
                          );
                        })}
                        <TableCell className="text-right">
                          <div className="flex items-center justify-end gap-1">
                            {allIdle && (
                              <Button
                                size="sm"
                                variant="outline"
                                disabled={publishMut.isPending}
                                onClick={() =>
                                  publishMut.mutate({
                                    contentId: row.id,
                                    platforms: platforms.map((p) => p.key),
                                  })
                                }
                              >
                                {isPendingFor(platforms.map((p) => p.key)) ? (
                                  <Loader2 className="h-3 w-3 animate-spin" />
                                ) : (
                                  <Send className="h-3 w-3" />
                                )}{" "}
                                최초 발행(전체)
                              </Button>
                            )}
                            <AlertDialog>
                              <AlertDialogTrigger asChild>
                                <button
                                  type="button"
                                  title="콘텐츠 삭제"
                                  className="h-8 w-8 grid place-items-center rounded-md text-muted-foreground hover:text-destructive hover:bg-destructive/10"
                                >
                                  <Trash2 className="h-4 w-4" />
                                </button>
                              </AlertDialogTrigger>
                              <AlertDialogContent>
                                <AlertDialogHeader>
                                  <AlertDialogTitle>이 콘텐츠를 삭제할까요?</AlertDialogTitle>
                                  <AlertDialogDescription>
                                    "{row.title || "(제목 없음)"}" 및 생성된 숏폼 영상이 삭제됩니다.
                                    이 작업은 되돌릴 수 없습니다. (이미 발행된 글은 지워지지 않아요.)
                                  </AlertDialogDescription>
                                </AlertDialogHeader>
                                <AlertDialogFooter>
                                  <AlertDialogCancel>취소</AlertDialogCancel>
                                  <AlertDialogAction
                                    onClick={() => deleteMut.mutate(row.id)}
                                    className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                                  >
                                    삭제
                                  </AlertDialogAction>
                                </AlertDialogFooter>
                              </AlertDialogContent>
                            </AlertDialog>
                          </div>
                        </TableCell>
                      </TableRow>
                    );
                  })
                )}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function StatusBadge({ status }: { status: PublishStatus }) {
  switch (status) {
    case "success":
      return <Badge className="bg-emerald-500 hover:bg-emerald-500">성공</Badge>;
    case "failed":
      return <Badge variant="destructive">실패</Badge>;
    case "queued":
      return <Badge className="bg-amber-500 hover:bg-amber-500">대기</Badge>;
    default:
      return <Badge variant="secondary">-</Badge>;
  }
}
