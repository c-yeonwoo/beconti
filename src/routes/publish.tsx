import { createFileRoute } from "@tanstack/react-router";
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
import { Send } from "lucide-react";

export const Route = createFileRoute("/publish")({
  head: () => ({
    meta: [
      { title: "배포 관리 · beconti" },
      { name: "description", content: "플랫폼별 배포 상태 및 재시도" },
    ],
  }),
  component: PublishPage,
});

const platforms = [
  { key: "naver_blog", label: "네이버 블로그" },
  { key: "naver_clip", label: "네이버 클립" },
  { key: "wordpress", label: "워드프레스" },
  { key: "instagram", label: "인스타그램" },
] as const;

function PublishPage() {
  const rows: Array<{
    id: string;
    title: string;
    createdAt: string;
    status: Record<string, "idle" | "queued" | "success" | "failed">;
  }> = [];

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">배포 관리</h1>
        <p className="text-sm text-muted-foreground">
          플랫폼별 발행 상태를 확인하고 실패한 항목을 재시도할 수 있습니다.
        </p>
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
                {rows.length === 0 ? (
                  <TableRow>
                    <TableCell
                      colSpan={platforms.length + 3}
                      className="text-center py-12 text-sm text-muted-foreground"
                    >
                      아직 배포 대기 중인 콘텐츠가 없습니다.
                    </TableCell>
                  </TableRow>
                ) : (
                  rows.map((row) => (
                    <TableRow key={row.id}>
                      <TableCell className="font-medium">{row.title}</TableCell>
                      <TableCell>{row.createdAt}</TableCell>
                      {platforms.map((p) => (
                        <TableCell key={p.key}>
                          <StatusBadge status={row.status[p.key]} />
                        </TableCell>
                      ))}
                      <TableCell className="text-right">
                        <Button size="sm" variant="outline">
                          <Send className="h-3 w-3" /> 발행
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  switch (status) {
    case "success":
      return (
        <Badge className="bg-emerald-500 hover:bg-emerald-500">성공</Badge>
      );
    case "failed":
      return <Badge variant="destructive">실패</Badge>;
    case "queued":
      return <Badge className="bg-amber-500 hover:bg-amber-500">대기</Badge>;
    default:
      return <Badge variant="secondary">-</Badge>;
  }
}
