import { createFileRoute, Link } from "@tanstack/react-router";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import {
  ArrowLeft,
  Loader2,
  Save,
  Send,
  RefreshCw,
  CheckCircle2,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import {
  getContentById,
  updateContent,
  publishContent,
  type GeneratedContent,
  type ScriptLine,
  type Platform,
  type PublishStatus,
} from "@/lib/api";

export const Route = createFileRoute("/content/$id")({
  head: () => ({ meta: [{ title: "콘텐츠 상세 · beconti" }] }),
  component: ContentDetailPage,
});

const PLATFORMS: { key: Platform; label: string }[] = [
  { key: "naver_blog", label: "네이버 블로그" },
  { key: "naver_clip", label: "네이버 클립" },
  { key: "instagram", label: "인스타그램" },
  { key: "wordpress", label: "워드프레스" },
];

function ContentDetailPage() {
  const { id } = Route.useParams();
  const qc = useQueryClient();

  const { data, isLoading, isError } = useQuery({
    queryKey: ["content", id],
    queryFn: () => getContentById(id),
  });

  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [script, setScript] = useState<ScriptLine[]>([]);

  useEffect(() => {
    if (data) {
      setTitle(data.title);
      setBody(data.body);
      setScript(data.script);
    }
  }, [data]);

  const saveMut = useMutation({
    mutationFn: () => updateContent(id, { title, body, script }),
    onSuccess: (updated) => {
      qc.setQueryData(["content", id], updated);
      qc.invalidateQueries({ queryKey: ["content"] });
      toast.success("저장되었습니다");
    },
    onError: (e: Error) => toast.error("저장 실패", { description: e.message }),
  });

  const publishMut = useMutation({
    mutationFn: (platform: Platform) =>
      publishContent({ contentId: id, platforms: [platform] }),
    onSuccess: (res, platform) => {
      qc.invalidateQueries({ queryKey: ["content", id] });
      qc.invalidateQueries({ queryKey: ["content"] });
      toast[res.ok ? "success" : "error"](
        res.ok ? "발행 완료" : "발행 실패",
        { description: PLATFORMS.find((p) => p.key === platform)?.label },
      );
    },
    onError: (e: Error) => toast.error("발행 요청 실패", { description: e.message }),
  });

  if (isLoading) {
    return (
      <div className="p-6 flex items-center gap-2 text-sm text-muted-foreground">
        <Loader2 className="h-4 w-4 animate-spin" /> 불러오는 중...
      </div>
    );
  }
  if (isError || !data) {
    return (
      <div className="p-6 text-sm text-destructive">
        콘텐츠를 불러오지 못했습니다. (백엔드 연결 확인)
      </div>
    );
  }

  const updateScript = (i: number, patch: Partial<ScriptLine>) =>
    setScript((prev) => prev.map((s, idx) => (idx === i ? { ...s, ...patch } : s)));

  const publishingPlatform = publishMut.isPending
    ? (publishMut.variables as Platform)
    : null;

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="icon" asChild>
            <Link to="/publish">
              <ArrowLeft className="h-4 w-4" />
            </Link>
          </Button>
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">콘텐츠 상세</h1>
            <p className="text-sm text-muted-foreground">
              내용을 수정하고 플랫폼별로 발행/재시도할 수 있습니다.
            </p>
          </div>
        </div>
        <Button onClick={() => saveMut.mutate()} disabled={saveMut.isPending}>
          {saveMut.isPending ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Save className="h-4 w-4" />
          )}{" "}
          저장
        </Button>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* 편집 영역 */}
        <div className="lg:col-span-2 space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">블로그 글</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="space-y-2">
                <Label>제목</Label>
                <Input value={title} onChange={(e) => setTitle(e.target.value)} />
              </div>
              <div className="space-y-2">
                <Label>본문 (마크다운)</Label>
                <Textarea
                  value={body}
                  onChange={(e) => setBody(e.target.value)}
                  className="min-h-[420px] font-mono text-sm"
                />
              </div>
            </CardContent>
          </Card>

          {script.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">숏폼 대본</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                {script.map((line, i) => (
                  <div key={i} className="grid grid-cols-[70px_1fr_1fr] gap-2">
                    <Input
                      value={line.time}
                      onChange={(e) => updateScript(i, { time: e.target.value })}
                      className="h-9 text-xs"
                    />
                    <Input
                      value={line.caption}
                      onChange={(e) => updateScript(i, { caption: e.target.value })}
                      placeholder="자막"
                      className="h-9 text-xs"
                    />
                    <Input
                      value={line.narration}
                      onChange={(e) => updateScript(i, { narration: e.target.value })}
                      placeholder="나레이션"
                      className="h-9 text-xs"
                    />
                  </div>
                ))}
              </CardContent>
            </Card>
          )}
        </div>

        {/* 플랫폼별 발행 */}
        <Card className="h-fit">
          <CardHeader>
            <CardTitle className="text-base">플랫폼별 발행</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {PLATFORMS.map((p) => {
              const status = data.platformStatus[p.key];
              const done = status === "success";
              const pending = publishingPlatform === p.key;
              return (
                <div
                  key={p.key}
                  className="flex items-center justify-between gap-2 border rounded-md p-2.5"
                >
                  <div className="flex items-center gap-2 text-sm">
                    <span className="font-medium">{p.label}</span>
                    <StatusBadge status={status} />
                  </div>
                  {done ? (
                    <span className="flex items-center gap-1 text-xs text-green-600">
                      <CheckCircle2 className="h-3.5 w-3.5" /> 완료
                    </span>
                  ) : (
                    <Button
                      size="sm"
                      variant={status === "failed" ? "ghost" : "outline"}
                      disabled={publishMut.isPending}
                      onClick={() => publishMut.mutate(p.key)}
                    >
                      {pending ? (
                        <Loader2 className="h-3 w-3 animate-spin" />
                      ) : status === "failed" ? (
                        <>
                          <RefreshCw className="h-3 w-3" /> 재시도
                        </>
                      ) : (
                        <>
                          <Send className="h-3 w-3" /> 발행
                        </>
                      )}
                    </Button>
                  )}
                </div>
              );
            })}
            <p className="text-xs text-muted-foreground pt-1">
              성공한 플랫폼은 재발행 버튼이 숨겨집니다. 발행 전 수정사항은 "저장"을
              먼저 눌러주세요.
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function StatusBadge({ status }: { status: PublishStatus }) {
  const map: Record<PublishStatus, { label: string; cls: string }> = {
    idle: { label: "대기", cls: "bg-muted text-muted-foreground" },
    queued: { label: "진행 중", cls: "bg-amber-100 text-amber-700" },
    success: { label: "성공", cls: "bg-green-100 text-green-700" },
    failed: { label: "실패", cls: "bg-red-100 text-red-700" },
  };
  const s = map[status] ?? map.idle;
  return <Badge className={`${s.cls} border-0 text-[10px]`}>{s.label}</Badge>;
}

export type { GeneratedContent };
