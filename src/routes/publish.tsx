import { createFileRoute } from "@tanstack/react-router";
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
import { Loader2, RefreshCw, Send } from "lucide-react";
import { toast } from "sonner";
import {
  listContent,
  publishContent,
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
  { key: "wordpress", label: "워드프레스" },
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
      toast[res.ok ? "success" : "error"](
        res.ok ? "발행 완료" : "일부 플랫폼 실패",
        { description: vars.platforms.join(", ") },
      );
    },
    onError: (e: Error) =>
      toast.error("발행 요청 실패", { description: e.message }),
  });

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">배포 관리</h1>
          <p className="text-sm text-muted-foreground">
            플랫폼별 발행 상태를 확인하고 실패한 항목을 재시도할 수 있습니다.
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
                    const hasFailed = platforms.some(
                      (p) => row.platformStatus[p.key] === "failed",
                    );
                    return (
                      <TableRow key={row.id}>
                        <TableCell className="font-medium max-w-[280px] truncate">
                          {row.title || "(제목 없음)"}
                        </TableCell>
                        <TableCell className="text-xs text-muted-foreground">
                          {new Date(row.createdAt).toLocaleString("ko-KR")}
                        </TableCell>
                        {platforms.map((p) => (
                          <TableCell key={p.key}>
                            <StatusBadge status={row.platformStatus[p.key]} />
                          </TableCell>
                        ))}
                        <TableCell className="text-right space-x-1">
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
                            <Send className="h-3 w-3" /> 발행
                          </Button>
                          {hasFailed && (
                            <Button
                              size="sm"
                              variant="ghost"
                              disabled={publishMut.isPending}
                              onClick={() =>
                                publishMut.mutate({
                                  contentId: row.id,
                                  platforms: platforms
                                    .filter((p) => row.platformStatus[p.key] === "failed")
                                    .map((p) => p.key),
                                })
                              }
                            >
                              <RefreshCw className="h-3 w-3" /> 재시도
                            </Button>
                          )}
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
