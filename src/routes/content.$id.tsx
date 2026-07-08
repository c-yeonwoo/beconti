import { createFileRoute, Link } from "@tanstack/react-router";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { ArrowLeft, Loader2, Save, Sparkles, X, Upload, Clapperboard, GripVertical } from "lucide-react";
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
import {
  getContentById,
  getContentSettings,
  updateContent,
  regenerateContent,
  makeVideo,
  uploadMedia,
  getDefaults,
  CATEGORIES,
  SCRIPT_STYLES,
  type ContentType,
  type ScriptStyle,
  type ScriptLine,
} from "@/lib/api";

export const Route = createFileRoute("/content/$id")({
  head: () => ({ meta: [{ title: "콘텐츠 상세 · beconti" }] }),
  component: ContentDetailPage,
});

interface MediaItem {
  mediaId: string;
  url: string;
}

function ContentDetailPage() {
  const { id } = Route.useParams();
  const qc = useQueryClient();

  const contentQ = useQuery({ queryKey: ["content", id], queryFn: () => getContentById(id) });
  const settingsQ = useQuery({ queryKey: ["settings", id], queryFn: () => getContentSettings(id) });
  const defaultsQ = useQuery({ queryKey: ["defaults"], queryFn: getDefaults, staleTime: Infinity });

  // 결과(수동 편집)
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [script, setScript] = useState<ScriptLine[]>([]);
  // 생성 설정
  const [keywords, setKeywords] = useState<string[]>([]);
  const [kwInput, setKwInput] = useState("");
  const [category, setCategory] = useState("");
  const [contentType, setContentType] = useState<ContentType>("place_review");
  const [scriptStyle, setScriptStyle] = useState<ScriptStyle>("polite");
  const [guideline, setGuideline] = useState("");
  const [hashtags, setHashtags] = useState<string[]>([]);
  const [tagInput, setTagInput] = useState("");
  const [placeName, setPlaceName] = useState("");
  const [placeUrl, setPlaceUrl] = useState("");
  const [media, setMedia] = useState<MediaItem[]>([]);
  const [dragIdx, setDragIdx] = useState<number | null>(null);
  const [videoVersion, setVideoVersion] = useState(0); // 재생성 시 캐시 무효화용

  const guidelinePlaceholder =
    (contentType === "vlog" ? defaultsQ.data?.video : defaultsQ.data?.blog) ??
    "비우면 유형별 기본 규칙이 적용됩니다.";

  useEffect(() => {
    const c = contentQ.data;
    if (c) {
      setTitle(c.title);
      setBody(c.body);
      setScript(c.script);
    }
  }, [contentQ.data]);

  useEffect(() => {
    const s = settingsQ.data;
    if (s) {
      setKeywords(s.keywords);
      setCategory(s.category);
      setContentType(s.contentType);
      setScriptStyle(s.scriptStyle);
      setGuideline(s.guideline);
      setHashtags(s.requiredHashtags);
      setPlaceName(s.placeName);
      setPlaceUrl(s.placeUrl);
      setMedia(s.media);
    }
  }, [settingsQ.data]);

  const saveMut = useMutation({
    mutationFn: () => updateContent(id, { title, body, script }),
    onSuccess: (u) => {
      qc.setQueryData(["content", id], u);
      qc.invalidateQueries({ queryKey: ["content"] });
      toast.success("저장되었습니다");
    },
    onError: (e: Error) => toast.error("저장 실패", { description: e.message }),
  });

  const regenMut = useMutation({
    mutationFn: () =>
      regenerateContent(id, {
        keywords,
        category,
        contentType,
        guideline,
        scriptStyle,
        requiredHashtags: hashtags,
        placeName,
        placeUrl,
        mediaIds: media.map((m) => m.mediaId),
      }),
    onSuccess: (u) => {
      setTitle(u.title);
      setBody(u.body);
      setScript(u.script);
      qc.setQueryData(["content", id], u);
      qc.invalidateQueries({ queryKey: ["content"] });
      qc.invalidateQueries({ queryKey: ["settings", id] });
      toast.success("AI 재생성 완료");
    },
    onError: (e: Error) =>
      toast.error("재생성 실패", {
        description: e.message + " · localhost:8000 백엔드 확인",
      }),
  });

  const videoMut = useMutation({
    mutationFn: () => makeVideo(id),
    onSuccess: (u) => {
      qc.setQueryData(["content", id], u);
      qc.invalidateQueries({ queryKey: ["content"] });
      setVideoVersion((v) => v + 1); // 같은 파일명이라 캐시 무효화
      toast.success("숏폼 영상 생성 완료", { description: "아래 미리보기에서 확인하세요." });
    },
    onError: (e: Error) =>
      toast.error("숏폼 생성 실패", { description: e.message }),
  });

  const addFiles = async (files: FileList | null) => {
    if (!files || !files.length) return;
    try {
      const arr = Array.from(files);
      const { mediaIds } = await uploadMedia(arr);
      setMedia((prev) => [
        ...prev,
        ...mediaIds.map((mid, i) => ({ mediaId: mid, url: URL.createObjectURL(arr[i]) })),
      ]);
    } catch (e) {
      toast.error("사진 업로드 실패");
    }
  };

  const updateScript = (i: number, patch: Partial<ScriptLine>) =>
    setScript((prev) => prev.map((s, idx) => (idx === i ? { ...s, ...patch } : s)));

  const moveScript = (from: number, to: number) => {
    if (from === to || from < 0 || to < 0) return;
    setScript((prev) => {
      const next = [...prev];
      const [row] = next.splice(from, 1);
      next.splice(to, 0, row);
      return next;
    });
  };

  if (contentQ.isLoading) {
    return (
      <div className="p-6 flex items-center gap-2 text-sm text-muted-foreground">
        <Loader2 className="h-4 w-4 animate-spin" /> 불러오는 중...
      </div>
    );
  }
  if (contentQ.isError || !contentQ.data) {
    return <div className="p-6 text-sm text-destructive">콘텐츠를 불러오지 못했습니다.</div>;
  }

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
              수정 후 <b>저장</b> → <b>숏폼 영상 생성</b>으로 영상 반영. 설정 바꿔 처음부터는 <b>AI 재생성</b>. (발행은 배포 관리)
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={() => regenMut.mutate()} disabled={regenMut.isPending || media.length === 0}>
            {regenMut.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}{" "}
            AI 재생성
          </Button>
          <Button variant="outline" onClick={() => videoMut.mutate()} disabled={videoMut.isPending}>
            {videoMut.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Clapperboard className="h-4 w-4" />}{" "}
            숏폼 영상 생성
          </Button>
          <Button onClick={() => saveMut.mutate()} disabled={saveMut.isPending}>
            {saveMut.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}{" "}
            저장
          </Button>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* 생성 설정 */}
        <Card className="h-fit">
          <CardHeader>
            <CardTitle className="text-base">생성 설정 (AI 재생성)</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label>사진 ({media.length})</Label>
              <div className="grid grid-cols-3 gap-2">
                {media.map((m) => (
                  <div key={m.mediaId} className="relative group aspect-square rounded-md overflow-hidden border bg-muted">
                    <img src={m.url} alt="" className="h-full w-full object-cover" />
                    <button
                      onClick={() => setMedia((prev) => prev.filter((x) => x.mediaId !== m.mediaId))}
                      className="absolute top-0.5 right-0.5 h-5 w-5 rounded-full bg-background/90 grid place-items-center opacity-0 group-hover:opacity-100"
                    >
                      <X className="h-3 w-3" />
                    </button>
                  </div>
                ))}
                <label className="aspect-square rounded-md border-2 border-dashed grid place-items-center cursor-pointer hover:bg-muted/40">
                  <Upload className="h-4 w-4 text-muted-foreground" />
                  <input type="file" multiple accept="image/*,video/*" className="hidden" onChange={(e) => addFiles(e.target.files)} />
                </label>
              </div>
            </div>

            <ChipField label="핵심 키워드" items={keywords} setItems={setKeywords} value={kwInput} setValue={setKwInput} placeholder="예: 성수동 카페" />

            <div className="space-y-2">
              <Label>카테고리</Label>
              <Select value={category} onValueChange={setCategory}>
                <SelectTrigger><SelectValue placeholder="카테고리 선택" /></SelectTrigger>
                <SelectContent>
                  {CATEGORIES.map((c) => (
                    <SelectItem key={c} value={c}>{c}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label>유형</Label>
              <Select value={contentType} onValueChange={(v) => setContentType(v as ContentType)}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="place_review">장소 리뷰</SelectItem>
                  <SelectItem value="product_review">제품 리뷰</SelectItem>
                  <SelectItem value="vlog">브이로그 (영상 중심)</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label>숏폼 대본 말투</Label>
              <Select value={scriptStyle} onValueChange={(v) => setScriptStyle(v as ScriptStyle)}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  {SCRIPT_STYLES.map((s) => (
                    <SelectItem key={s.value} value={s.value}>{s.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <ChipField label="필수 해시태그" items={hashtags} setItems={setHashtags} value={tagInput} setValue={setTagInput} placeholder="예: 성수동카페" hash />

            <div className="space-y-2">
              <Label>매장명 (지도, 선택)</Label>
              <Input value={placeName} onChange={(e) => setPlaceName(e.target.value)} placeholder="예: 스타벅스 강남대로점" />
            </div>

            <div className="space-y-2">
              <Label>네이버 지도 링크 (선택)</Label>
              <Input value={placeUrl} onChange={(e) => setPlaceUrl(e.target.value)} placeholder="링크 있으면 우선 사용, 없으면 매장명 검색" />
            </div>

            <div className="space-y-2">
              <Label>캠페인 가이드라인</Label>
              <Textarea value={guideline} onChange={(e) => setGuideline(e.target.value)} className="min-h-[110px] text-sm" placeholder={guidelinePlaceholder} />
            </div>
            <p className="text-xs text-muted-foreground">
              설정을 바꾸고 상단 <b>AI 재생성</b>을 누르면 제목·본문·대본이 새로 만들어집니다.
            </p>
          </CardContent>
        </Card>

        {/* 결과 (수동 편집) */}
        <div className="lg:col-span-2 space-y-6">
          {contentQ.data.videoUrl && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">숏폼 미리보기</CardTitle>
                <p className="text-xs text-muted-foreground">
                  발행 전 확인용. 자막·대본 수정 후 상단 "숏폼 영상 생성"을 다시 누르면 갱신됩니다.
                </p>
              </CardHeader>
              <CardContent>
                <video
                  key={videoVersion}
                  src={`${contentQ.data.videoUrl}?v=${videoVersion}`}
                  controls
                  playsInline
                  className="mx-auto aspect-[9/16] max-h-[520px] rounded-md border bg-black"
                />
              </CardContent>
            </Card>
          )}

          <Card>
            <CardHeader><CardTitle className="text-base">블로그 글</CardTitle></CardHeader>
            <CardContent className="space-y-3">
              <div className="space-y-2">
                <Label>제목</Label>
                <Input value={title} onChange={(e) => setTitle(e.target.value)} />
              </div>
              <div className="space-y-2">
                <Label>본문 (마크다운)</Label>
                <Textarea value={body} onChange={(e) => setBody(e.target.value)} className="min-h-[420px] font-mono text-sm" />
              </div>
            </CardContent>
          </Card>

          {script.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">숏폼 대본</CardTitle>
                <p className="text-xs text-muted-foreground">
                  왼쪽 손잡이를 잡고 드래그해 자막 순서를 바꿀 수 있어요. 수정 후 저장 → 숏폼 영상 생성.
                </p>
              </CardHeader>
              <CardContent className="space-y-1.5">
                <div className="grid grid-cols-[24px_70px_1fr_1fr] gap-2 px-1 text-[11px] text-muted-foreground">
                  <span /> <span>시간</span> <span>자막</span> <span>나레이션</span>
                </div>
                {script.map((line, i) => (
                  <div
                    key={i}
                    className={`grid grid-cols-[24px_70px_1fr_1fr] gap-2 items-center rounded-md ${
                      dragIdx === i ? "opacity-40" : ""
                    }`}
                    onDragOver={(e) => e.preventDefault()}
                    onDrop={(e) => {
                      e.preventDefault();
                      if (dragIdx !== null) moveScript(dragIdx, i);
                      setDragIdx(null);
                    }}
                  >
                    <button
                      type="button"
                      draggable
                      onDragStart={() => setDragIdx(i)}
                      onDragEnd={() => setDragIdx(null)}
                      className="h-9 grid place-items-center cursor-grab active:cursor-grabbing text-muted-foreground hover:text-foreground"
                      title="드래그해서 순서 변경"
                    >
                      <GripVertical className="h-4 w-4" />
                    </button>
                    <Input value={line.time} onChange={(e) => updateScript(i, { time: e.target.value })} className="h-9 text-xs" />
                    <Input value={line.caption} onChange={(e) => updateScript(i, { caption: e.target.value })} placeholder="자막" className="h-9 text-xs" />
                    <Input value={line.narration} onChange={(e) => updateScript(i, { narration: e.target.value })} placeholder="나레이션" className="h-9 text-xs" />
                  </div>
                ))}
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}

function ChipField({
  label, items, setItems, value, setValue, placeholder, hash,
}: {
  label: string;
  items: string[];
  setItems: (v: string[]) => void;
  value: string;
  setValue: (v: string) => void;
  placeholder?: string;
  hash?: boolean;
}) {
  const add = () => {
    let v = value.trim();
    if (!v) return;
    if (hash && !v.startsWith("#")) v = `#${v}`;
    if (items.includes(v)) return;
    setItems([...items, v]);
    setValue("");
  };
  return (
    <div className="space-y-2">
      <Label>{label}</Label>
      <div className="flex gap-2">
        <Input
          value={value}
          placeholder={placeholder}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.nativeEvent.isComposing && e.keyCode !== 229) {
              e.preventDefault();
              add();
            }
          }}
        />
        <Button type="button" variant="outline" onClick={add}>추가</Button>
      </div>
      <div className="flex flex-wrap gap-1.5">
        {items.map((it) => (
          <Badge key={it} variant="secondary" className="cursor-pointer" onClick={() => setItems(items.filter((x) => x !== it))}>
            {it} <X className="h-3 w-3 ml-1" />
          </Badge>
        ))}
      </div>
    </div>
  );
}
