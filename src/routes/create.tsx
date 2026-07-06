import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useCallback, useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import {
  Upload,
  X,
  Sparkles,
  Loader2,
  ArrowLeft,
  Save,
  Send,
  Clapperboard,
  CheckCircle2,
  AlertCircle,
  ShieldCheck,
} from "lucide-react";
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
  makeVideo,
  checkCompliance,
  getDefaults,
  CATEGORIES,
  type ContentType,
  type GeneratedContent,
  type ScriptLine,
  type ComplianceResult,
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
  const [category, setCategory] = useState("");
  const [placeName, setPlaceName] = useState("");
  const [placeUrl, setPlaceUrl] = useState("");
  const [contentType, setContentType] = useState<ContentType>("place_review");
  const [hashtagInput, setHashtagInput] = useState("");
  const [hashtags, setHashtags] = useState<string[]>([]);
  const [guideline, setGuideline] = useState("");
  const [dragging, setDragging] = useState(false);
  const [result, setResult] = useState<GeneratedContent | null>(null);

  const defaultsQ = useQuery({ queryKey: ["defaults"], queryFn: getDefaults, staleTime: Infinity });
  const guidelinePlaceholder =
    (contentType === "vlog" ? defaultsQ.data?.video : defaultsQ.data?.blog) ??
    "체험단 가이드라인을 붙여넣으세요 (비우면 유형별 기본 규칙 적용)";

  const mutation = useMutation({
    mutationFn: async () => {
      const { mediaIds } = await uploadMedia(media.map((m) => m.file));
      return generateContent({
        keywords,
        category,
        contentType,
        guideline,
        requiredHashtags: hashtags,
        placeName,
        placeUrl,
        mediaIds,
      });
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

  const addHashtag = () => {
    let h = hashtagInput.trim();
    if (!h) return;
    if (!h.startsWith("#")) h = `#${h}`;
    if (hashtags.includes(h)) return;
    setHashtags([...hashtags, h]);
    setHashtagInput("");
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
                      if (
                        e.key === "Enter" &&
                        !e.nativeEvent.isComposing &&
                        e.keyCode !== 229
                      ) {
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
                <Label>카테고리</Label>
                <Select value={category} onValueChange={setCategory}>
                  <SelectTrigger>
                    <SelectValue placeholder="카테고리 선택" />
                  </SelectTrigger>
                  <SelectContent>
                    {CATEGORIES.map((c) => (
                      <SelectItem key={c} value={c}>
                        {c}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label>매장명 (지도 첨부용, 선택)</Label>
                <Input
                  value={placeName}
                  placeholder="예: 스타벅스 강남대로점"
                  onChange={(e) => setPlaceName(e.target.value)}
                />
              </div>

              <div className="space-y-2">
                <Label>네이버 지도 링크 (선택)</Label>
                <Input
                  value={placeUrl}
                  placeholder="링크 있으면 우선 사용, 없으면 매장명으로 검색"
                  onChange={(e) => setPlaceUrl(e.target.value)}
                />
                <p className="text-xs text-muted-foreground">
                  매장명 또는 지도 링크가 있으면 발행 시 지도(장소 카드)가 자동 첨부됩니다.
                </p>
              </div>

              <div className="space-y-2">
                <Label>유형</Label>
                <Select
                  value={contentType}
                  onValueChange={(v) => setContentType(v as ContentType)}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="place_review">장소 리뷰</SelectItem>
                    <SelectItem value="product_review">제품 리뷰</SelectItem>
                    <SelectItem value="vlog">브이로그 (영상 중심)</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label>필수 해시태그</Label>
                <div className="flex gap-2">
                  <Input
                    value={hashtagInput}
                    placeholder="예: 성수동카페"
                    onChange={(e) => setHashtagInput(e.target.value)}
                    onKeyDown={(e) => {
                      if (
                        e.key === "Enter" &&
                        !e.nativeEvent.isComposing &&
                        e.keyCode !== 229
                      ) {
                        e.preventDefault();
                        addHashtag();
                      }
                    }}
                  />
                  <Button type="button" variant="outline" onClick={addHashtag}>
                    추가
                  </Button>
                </div>
                <div className="flex flex-wrap gap-1.5 pt-1">
                  {hashtags.map((h) => (
                    <Badge
                      key={h}
                      variant="secondary"
                      className="cursor-pointer"
                      onClick={() => setHashtags(hashtags.filter((x) => x !== h))}
                    >
                      {h} <X className="h-3 w-3 ml-1" />
                    </Badge>
                  ))}
                </div>
              </div>

              <div className="space-y-2">
                <Label>캠페인 가이드라인</Label>
                <Textarea
                  value={guideline}
                  placeholder={guidelinePlaceholder}
                  onChange={(e) => setGuideline(e.target.value)}
                  className="min-h-[120px] text-sm"
                />
                <p className="text-xs text-muted-foreground">
                  비워두면 위 회색 텍스트(유형별 기본 규칙)가 자동 적용됩니다.
                </p>
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
        <ResultView
          result={result}
          setResult={setResult}
          keywords={keywords}
          hashtags={hashtags}
          guideline={guideline}
          photoCount={media.length}
        />
      )}
    </div>
  );
}

function ResultView({
  result,
  setResult,
  keywords,
  hashtags,
  guideline,
  photoCount,
}: {
  result: GeneratedContent | null;
  setResult: (r: GeneratedContent) => void;
  keywords: string[];
  hashtags: string[];
  guideline: string;
  photoCount: number;
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

  const videoMutation = useMutation({
    mutationFn: () => makeVideo(safe.id),
    onSuccess: (data) => {
      setResult(data);
      toast.success("숏폼 영상 생성 완료");
    },
    onError: (err: Error) => {
      toast.error("숏폼 생성 실패", { description: err.message });
    },
  });

  const [compliance, setCompliance] = useState<ComplianceResult | null>(null);
  const complianceMutation = useMutation({
    mutationFn: () =>
      checkCompliance({
        body: safe.body,
        keywords,
        requiredHashtags: hashtags,
        guideline,
        photoCount,
      }),
    onSuccess: setCompliance,
  });

  // 결과가 처음 로드되면 자동 1회 검사
  useEffect(() => {
    if (safe.body) complianceMutation.mutate();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

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
              className="min-h-[360px] font-mono text-sm"
            />
          </div>

          <div className="space-y-2 rounded-md border p-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-sm font-medium">
                <ShieldCheck className="h-4 w-4" />
                캠페인 준수 체크
                {compliance && (
                  <span
                    className={cn(
                      "text-xs font-normal",
                      compliance.passed === compliance.total
                        ? "text-green-600"
                        : "text-amber-600",
                    )}
                  >
                    {compliance.passed}/{compliance.total} 통과
                  </span>
                )}
              </div>
              <Button
                variant="ghost"
                size="sm"
                className="h-7 text-xs"
                disabled={complianceMutation.isPending}
                onClick={() => complianceMutation.mutate()}
              >
                {complianceMutation.isPending ? (
                  <Loader2 className="h-3 w-3 animate-spin" />
                ) : (
                  "다시 검사"
                )}
              </Button>
            </div>
            {compliance ? (
              <ul className="space-y-1">
                {compliance.checks.map((c, i) => (
                  <li key={i} className="flex items-center gap-2 text-xs">
                    {c.ok ? (
                      <CheckCircle2 className="h-3.5 w-3.5 shrink-0 text-green-600" />
                    ) : (
                      <AlertCircle className="h-3.5 w-3.5 shrink-0 text-amber-600" />
                    )}
                    <span
                      className={c.ok ? "text-muted-foreground" : "text-foreground"}
                    >
                      {c.label}
                    </span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-xs text-muted-foreground">검사 중...</p>
            )}
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
                아래 "숏폼 영상 생성"을 누르면<br />사진 + 자막 영상이 만들어집니다
              </div>
            )}
          </div>

          <Button
            variant="outline"
            className="w-full"
            disabled={videoMutation.isPending || safe.script.length === 0}
            onClick={() => videoMutation.mutate()}
          >
            {videoMutation.isPending ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" /> 영상 생성 중... (수십 초)
              </>
            ) : (
              <>
                <Clapperboard className="h-4 w-4" />{" "}
                {safe.videoUrl ? "숏폼 다시 생성" : "숏폼 영상 생성"}
              </>
            )}
          </Button>

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
