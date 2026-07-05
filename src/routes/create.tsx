import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useMutation } from "@tanstack/react-query";
import { useCallback, useMemo, useState } from "react";
import { toast } from "sonner";
import { Upload, X, Sparkles, Loader2, ArrowLeft, Save, Send } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { cn } from "@/lib/utils";
import {
  generateContent,
  uploadMedia,
  type GeneratedContent,
  type ScriptLine,
} from "@/lib/api";

export const Route = createFileRoute("/create")({
  head: () => ({
    meta: [
      { title: "콘텐츠 생성 · beconti" },
      { name: "description", content: "미디어를 업로드해 블로그와 숏폼 콘텐츠 생성" },
    ],
  }),
  component: CreatePage,
});

interface MediaItem {
  file: File;
  url: string;
}

function CreatePage() {
  const [step, setStep] = useState<"input" | "result">("input");
  const [media, setMedia] = useState<MediaItem[]>([]);
  const [keywordInput, setKeywordInput] = useState("");
  const [keywords, setKeywords] = useState<string[]>([]);
  const [tone, setTone] = useState("review");
  const [dragging, setDragging] = useState(false);
  const [result, setResult] = useState<GeneratedContent | null>(null);

  const mutation = useMutation({
    mutationFn: async () => {
      const { mediaIds } = await uploadMedia(media.map((m) => m.file));
      return generateContent({ keywords, tone, mediaIds });
    },
    onSuccess: (data) => {
      setResult(data);
      setStep("result");
      toast.success("콘텐츠 생성 완료");
    },
    onError: (err: Error) => {
      toast.error("생성 실패", {
        description:
          err.message + " · localhost:8000 백엔드가 실행 중인지 확인하세요.",
      });
    },
  });

  const addFiles = useCallback((files: FileList | File[]) => {
    const arr = Array.from(files);
    setMedia((prev) => [
      ...prev,
      ...arr.map((f) => ({ file: f, url: URL.createObjectURL(f) })),
    ]);
  }, []);

  const removeMedia = (idx: number) => {
    setMedia((prev) => {
      URL.revokeObjectURL(prev[idx].url);
      return prev.filter((_, i) => i !== idx);
    });
  };

  const addKeyword = () => {
    const k = keywordInput.trim();
    if (!k) return;
    if (keywords.includes(k)) return;
    setKeywords([...keywords, k]);
    setKeywordInput("");
  };

  const canGenerate = media.length > 0 && keywords.length > 0;

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">콘텐츠 생성</h1>
          <p className="text-sm text-muted-foreground">
            사진/영상과 키워드를 넣으면 블로그 글과 숏폼 대본을 함께 만듭니다.
          </p>
        </div>
        {step === "result" && (
          <Button variant="outline" onClick={() => setStep("input")}>
            <ArrowLeft className="h-4 w-4" /> 다시 생성
          </Button>
        )}
      </div>

      {step === "input" ? (
        <div className="grid gap-6 lg:grid-cols-3">
          <Card className="lg:col-span-2">
            <CardHeader>
              <CardTitle className="text-base">미디어 업로드</CardTitle>
            </CardHeader>
            <CardContent>
              <label
                onDragOver={(e) => {
                  e.preventDefault();
                  setDragging(true);
                }}
                onDragLeave={() => setDragging(false)}
                onDrop={(e) => {
                  e.preventDefault();
                  setDragging(false);
                  addFiles(e.dataTransfer.files);
                }}
                className={cn(
                  "flex flex-col items-center justify-center rounded-lg border-2 border-dashed p-10 cursor-pointer transition-colors",
                  dragging
                    ? "border-primary bg-primary/5"
                    : "border-border hover:bg-muted/40",
                )}
              >
                <Upload className="h-8 w-8 text-muted-foreground" />
                <p className="mt-3 text-sm font-medium">
                  이미지/영상 파일을 여기에 드롭하세요
                </p>
                <p className="text-xs text-muted-foreground">
                  또는 클릭해서 선택 (다중 선택 가능)
                </p>
                <input
                  type="file"
                  multiple
                  accept="image/*,video/*"
                  className="hidden"
                  onChange={(e) => e.target.files && addFiles(e.target.files)}
                />
              </label>

              {media.length > 0 && (
                <div className="mt-4 grid grid-cols-3 md:grid-cols-4 gap-3">
                  {media.map((m, i) => (
                    <div
                      key={i}
                      className="relative group aspect-square rounded-md overflow-hidden border bg-muted"
                    >
                      {m.file.type.startsWith("video/") ? (
                        <video
                          src={m.url}
                          className="h-full w-full object-cover"
                        />
                      ) : (
                        <img
                          src={m.url}
                          alt=""
                          className="h-full w-full object-cover"
                        />
                      )}
                      <button
                        onClick={() => removeMedia(i)}
                        className="absolute top-1 right-1 h-6 w-6 rounded-full bg-background/90 grid place-items-center opacity-0 group-hover:opacity-100 transition"
                      >
                        <X className="h-3 w-3" />
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">설정</CardTitle>
            </CardHeader>
            <CardContent className="space-y-5">
              <div className="space-y-2">
                <Label>핵심 키워드</Label>
                <div className="flex gap-2">
                  <Input
                    value={keywordInput}
                    placeholder="예: 성수동 카페"
                    onChange={(e) => setKeywordInput(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") {
                        e.preventDefault();
                        addKeyword();
                      }
                    }}
                  />
                  <Button type="button" variant="outline" onClick={addKeyword}>
                    추가
                  </Button>
                </div>
                <div className="flex flex-wrap gap-1.5 pt-1">
                  {keywords.map((k) => (
                    <Badge
                      key={k}
                      variant="secondary"
                      className="cursor-pointer"
                      onClick={() =>
                        setKeywords(keywords.filter((x) => x !== k))
                      }
                    >
                      {k} <X className="h-3 w-3 ml-1" />
                    </Badge>
                  ))}
                </div>
              </div>

              <div className="space-y-2">
                <Label>톤 / 스타일</Label>
                <Select value={tone} onValueChange={setTone}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="review">리뷰형</SelectItem>
                    <SelectItem value="info">정보형</SelectItem>
                    <SelectItem value="daily">일상형</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <Button
                className="w-full"
                disabled={!canGenerate || mutation.isPending}
                onClick={() => mutation.mutate()}
              >
                {mutation.isPending ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" /> 생성 중...
                  </>
                ) : (
                  <>
                    <Sparkles className="h-4 w-4" /> 생성하기
                  </>
                )}
              </Button>
              {!canGenerate && (
                <p className="text-xs text-muted-foreground">
                  미디어와 키워드를 하나 이상 추가해 주세요.
                </p>
              )}
            </CardContent>
          </Card>
        </div>
      ) : (
        <ResultView result={result} setResult={setResult} />
      )}
    </div>
  );
}

function ResultView({
  result,
  setResult,
}: {
  result: GeneratedContent | null;
  setResult: (r: GeneratedContent) => void;
}) {
  const navigate = useNavigate();
  const safe = useMemo<GeneratedContent>(
    () =>
      result ?? {
        id: "draft",
        title: "",
        body: "",
        script: [],
        createdAt: new Date().toISOString(),
        platformStatus: {
          naver_blog: "idle",
          naver_clip: "idle",
          wordpress: "idle",
          instagram: "idle",
        },
      },
    [result],
  );

  const updateScript = (idx: number, patch: Partial<ScriptLine>) => {
    const next = [...safe.script];
    next[idx] = { ...next[idx], ...patch };
    setResult({ ...safe, script: next });
  };

  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <Card>
        <CardHeader>
          <CardTitle className="text-base">블로그 글</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="space-y-2">
            <Label>제목</Label>
            <Input
              value={safe.title}
              onChange={(e) => setResult({ ...safe, title: e.target.value })}
              placeholder="블로그 제목"
            />
          </div>
          <div className="space-y-2">
            <Label>본문 (마크다운)</Label>
            <Textarea
              value={safe.body}
              onChange={(e) => setResult({ ...safe, body: e.target.value })}
              placeholder="AI가 작성한 본문이 여기에 표시됩니다"
              className="min-h-[420px] font-mono text-sm"
            />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">숏폼 · 자막 편집</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="aspect-[9/16] max-h-[320px] mx-auto w-full bg-muted rounded-md grid place-items-center border">
            {safe.videoUrl ? (
              <video
                src={safe.videoUrl}
                controls
                className="h-full w-full rounded-md"
              />
            ) : (
              <div className="text-center text-xs text-muted-foreground p-4">
                Creatomate 렌더 완료 시<br />영상 미리보기가 표시됩니다
              </div>
            )}
          </div>

          <div className="space-y-2">
            <Label>대본 (시간 · 자막 · 나레이션)</Label>
            <div className="space-y-2 max-h-[280px] overflow-y-auto pr-1">
              {safe.script.length === 0 && (
                <div className="text-xs text-muted-foreground text-center py-6 border rounded-md">
                  대본이 생성되면 여기에 표시됩니다
                </div>
              )}
              {safe.script.map((line, i) => (
                <div
                  key={i}
                  className="grid grid-cols-[60px_1fr_1fr] gap-2 items-start"
                >
                  <Input
                    value={line.time}
                    onChange={(e) => updateScript(i, { time: e.target.value })}
                    className="h-9 text-xs"
                  />
                  <Input
                    value={line.caption}
                    onChange={(e) =>
                      updateScript(i, { caption: e.target.value })
                    }
                    placeholder="자막"
                    className="h-9 text-xs"
                  />
                  <Input
                    value={line.narration}
                    onChange={(e) =>
                      updateScript(i, { narration: e.target.value })
                    }
                    placeholder="나레이션"
                    className="h-9 text-xs"
                  />
                </div>
              ))}
            </div>
          </div>

          <div className="flex gap-2 pt-2">
            <Button
              variant="outline"
              className="flex-1"
              onClick={() => toast.success("초안이 저장되었습니다", { description: "생성 시 서버에 자동 저장됩니다." })}
            >
              <Save className="h-4 w-4" /> 저장
            </Button>
            <Button className="flex-1" onClick={() => navigate({ to: "/publish" })}>
              <Send className="h-4 w-4" /> 배포 관리로
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
