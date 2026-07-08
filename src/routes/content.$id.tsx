import { createFileRoute, Link } from "@tanstack/react-router";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import {
  ArrowLeft,
  Loader2,
  Save,
  Sparkles,
  X,
  Upload,
  Clapperboard,
  GripVertical,
  Film,
  Wand2,
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
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from "@/components/ui/sheet";
import {
  getContentById,
  getContentSettings,
  updateContent,
  regenerateBlog,
  regenerateScript,
  makeVideo,
  uploadMedia,
  getDefaults,
  CATEGORIES,
  SCRIPT_STYLES,
  CAPTION_STYLES,
  type ContentType,
  type ScriptStyle,
  type CaptionStyle,
  type ScriptLine,
  type GeneratePayload,
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

  // 블로그 (수동 편집)
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  // 숏폼 대본
  const [script, setScript] = useState<ScriptLine[]>([]);
  // 설정
  const [keywords, setKeywords] = useState<string[]>([]);
  const [kwInput, setKwInput] = useState("");
  const [category, setCategory] = useState("");
  const [contentType, setContentType] = useState<ContentType>("place_review");
  const [blogGuideline, setBlogGuideline] = useState("");
  const [shortsGuideline, setShortsGuideline] = useState("");
  const [scriptStyle, setScriptStyle] = useState<ScriptStyle>("polite");
  const [captionStyle, setCaptionStyle] = useState<CaptionStyle>("basic");
  const [hashtags, setHashtags] = useState<string[]>([]);
  const [tagInput, setTagInput] = useState("");
  const [placeName, setPlaceName] = useState("");
  const [placeUrl, setPlaceUrl] = useState("");
  const [media, setMedia] = useState<MediaItem[]>([]);
  const [dragIdx, setDragIdx] = useState<number | null>(null);
  const [videoVersion, setVideoVersion] = useState(0);
  const [shortsOpen, setShortsOpen] = useState(false);

  const hasVideo = media.some((m) => /\.(mp4|mov|m4v|webm|avi|mkv)$/i.test(m.url));

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
      setBlogGuideline(s.blogGuideline);
      setShortsGuideline(s.shortsGuideline);
      setScriptStyle(s.scriptStyle);
      setCaptionStyle(s.captionStyle);
      setHashtags(s.requiredHashtags);
      setPlaceName(s.placeName);
      setPlaceUrl(s.placeUrl);
      setMedia(s.media);
    }
  }, [settingsQ.data]);

  const payload = (): GeneratePayload => ({
    keywords,
    category,
    contentType,
    blogGuideline,
    shortsGuideline,
    scriptStyle,
    captionStyle,
    requiredHashtags: hashtags,
    placeName,
    placeUrl,
    mediaIds: media.map((m) => m.mediaId),
  });

  const saveMut = useMutation({
    mutationFn: () => updateContent(id, { title, body, script }),
    onSuccess: (u) => {
      qc.setQueryData(["content", id], u);
      qc.invalidateQueries({ queryKey: ["content"] });
      toast.success("저장되었습니다");
    },
    onError: (e: Error) => toast.error("저장 실패", { description: e.message }),
  });

  const regenBlogMut = useMutation({
    mutationFn: () => regenerateBlog(id, payload()),
    onSuccess: (u) => {
      setTitle(u.title);
      setBody(u.body);
      qc.setQueryData(["content", id], u);
      qc.invalidateQueries({ queryKey: ["content"] });
      qc.invalidateQueries({ queryKey: ["settings", id] });
      toast.success("블로그 글 재생성 완료");
    },
    onError: (e: Error) =>
      toast.error("블로그 재생성 실패", { description: e.message }),
  });

  const regenScriptMut = useMutation({
    mutationFn: () => regenerateScript(id, payload()),
    onSuccess: (u) => {
      setScript(u.script);
      qc.setQueryData(["content", id], u);
      qc.invalidateQueries({ queryKey: ["content"] });
      qc.invalidateQueries({ queryKey: ["settings", id] });
      toast.success("숏폼 대본 생성 완료");
    },
    onError: (e: Error) =>
      toast.error("대본 생성 실패", { description: e.message }),
  });

  const videoMut = useMutation({
    mutationFn: () => makeVideo(id),
    onSuccess: (u) => {
      qc.setQueryData(["content", id], u);
      qc.invalidateQueries({ queryKey: ["content"] });
      setVideoVersion((v) => v + 1);
      toast.success("숏폼 영상 생성 완료", { description: "미리보기에서 확인하세요." });
    },
    onError: (e: Error) => toast.error("숏폼 생성 실패", { description: e.message }),
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
    } catch {
      toast.error("사진/영상 업로드 실패");
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

  const videoUrl = contentQ.data.videoUrl;

  return (
    <div className="p-6 space-y-6">
      {/* 헤더 */}
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-3 min-w-0">
          <Button variant="ghost" size="icon" asChild>
            <Link to="/publish">
              <ArrowLeft className="h-4 w-4" />
            </Link>
          </Button>
          <div className="min-w-0">
            <h1 className="text-2xl font-semibold tracking-tight">블로그 글 작성</h1>
            <p className="text-sm text-muted-foreground">
              메인은 블로그 글입니다. 숏폼이 필요하면 우측 "숏폼 만들기"로.
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <Button variant="outline" onClick={() => setShortsOpen(true)}>
            <Film className="h-4 w-4" /> 숏폼 만들기
            {script.length > 0 && (
              <Badge variant="secondary" className="ml-1">{script.length}</Badge>
            )}
          </Button>
          <Button onClick={() => saveMut.mutate()} disabled={saveMut.isPending}>
            {saveMut.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}{" "}
            저장
          </Button>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* 좌: 글 설정 */}
        <Card className="h-fit">
          <CardHeader>
            <CardTitle className="text-base">글 설정</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label>사진/영상 ({media.length})</Label>
              <div className="grid grid-cols-3 gap-2">
                {media.map((m) => (
                  <div key={m.mediaId} className="relative group aspect-square rounded-md overflow-hidden border bg-muted">
                    {/\.(mp4|mov|m4v|webm|avi|mkv)$/i.test(m.url) ? (
                      <video src={m.url} className="h-full w-full object-cover" />
                    ) : (
                      <img src={m.url} alt="" className="h-full w-full object-cover" />
                    )}
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
                  {CATEGORIES.map((c) => <SelectItem key={c} value={c}>{c}</SelectItem>)}
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
                  <SelectItem value="vlog">브이로그</SelectItem>
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
              <Input value={placeUrl} onChange={(e) => setPlaceUrl(e.target.value)} placeholder="링크 있으면 우선, 없으면 매장명 검색" />
            </div>

            <div className="space-y-2">
              <Label>블로그 가이드라인</Label>
              <Textarea
                value={blogGuideline}
                onChange={(e) => setBlogGuideline(e.target.value)}
                className="min-h-[100px] text-sm"
                placeholder={defaultsQ.data?.blog ?? "비우면 기본 규칙 적용"}
              />
            </div>

            <Button
              className="w-full"
              variant="outline"
              disabled={regenBlogMut.isPending || media.length === 0}
              onClick={() => regenBlogMut.mutate()}
            >
              {regenBlogMut.isPending ? (
                <><Loader2 className="h-4 w-4 animate-spin" /> 재생성 중...</>
              ) : (
                <><Wand2 className="h-4 w-4" /> 블로그 글 재생성</>
              )}
            </Button>
          </CardContent>
        </Card>

        {/* 우: 블로그 글 */}
        <div className="lg:col-span-2">
          <Card>
            <CardHeader><CardTitle className="text-base">블로그 글</CardTitle></CardHeader>
            <CardContent className="space-y-3">
              <div className="space-y-2">
                <Label>제목</Label>
                <Input value={title} onChange={(e) => setTitle(e.target.value)} />
              </div>
              <div className="space-y-2">
                <Label>본문 (마크다운)</Label>
                <Textarea value={body} onChange={(e) => setBody(e.target.value)} className="min-h-[560px] font-mono text-sm" />
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* 숏폼 관리 Sheet */}
      <Sheet open={shortsOpen} onOpenChange={setShortsOpen}>
        <SheetContent side="right" className="w-full sm:max-w-xl overflow-y-auto">
          <SheetHeader>
            <SheetTitle className="flex items-center gap-2">
              <Film className="h-4 w-4" /> 숏폼 만들기 (선택)
            </SheetTitle>
            <SheetDescription>
              영상을 올린 콘텐츠만 숏폼을 만들 수 있어요. 대본 생성 → 영상 생성 순서입니다.
            </SheetDescription>
          </SheetHeader>

          <div className="mt-4 space-y-5">
            {!hasVideo && (
              <div className="rounded-md border border-dashed p-4 text-sm text-muted-foreground text-center">
                숏폼을 만들려면 좌측 "글 설정"에서 <b>영상</b>을 업로드하고 저장하세요.
              </div>
            )}

            {/* 대본 스타일 */}
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-2">
                <Label>대본 말투</Label>
                <Select value={scriptStyle} onValueChange={(v) => setScriptStyle(v as ScriptStyle)}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {SCRIPT_STYLES.map((s) => <SelectItem key={s.value} value={s.value}>{s.label}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>자막 스타일</Label>
                <Select value={captionStyle} onValueChange={(v) => setCaptionStyle(v as CaptionStyle)}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {CAPTION_STYLES.map((s) => <SelectItem key={s.value} value={s.value}>{s.label}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="space-y-2">
              <Label>숏폼 대본 가이드라인</Label>
              <Textarea
                value={shortsGuideline}
                onChange={(e) => setShortsGuideline(e.target.value)}
                className="min-h-[80px] text-sm"
                placeholder={defaultsQ.data?.video ?? "비우면 기본 규칙 적용"}
              />
            </div>

            <Button
              className="w-full"
              disabled={regenScriptMut.isPending || !hasVideo}
              onClick={() => regenScriptMut.mutate()}
            >
              {regenScriptMut.isPending ? (
                <><Loader2 className="h-4 w-4 animate-spin" /> 대본 생성 중...</>
              ) : (
                <><Sparkles className="h-4 w-4" /> {script.length ? "대본 재생성" : "숏폼 대본 생성"}</>
              )}
            </Button>

            {/* 대본 편집 */}
            {script.length > 0 && (
              <div className="space-y-2">
                <Label>대본 (드래그로 순서 변경)</Label>
                <div className="space-y-1.5">
                  {script.map((line, i) => (
                    <div
                      key={i}
                      className={`grid grid-cols-[20px_60px_1fr] gap-1.5 items-center ${dragIdx === i ? "opacity-40" : ""}`}
                      onDragOver={(e) => e.preventDefault()}
                      onDrop={(e) => { e.preventDefault(); if (dragIdx !== null) moveScript(dragIdx, i); setDragIdx(null); }}
                    >
                      <button
                        type="button"
                        draggable
                        onDragStart={() => setDragIdx(i)}
                        onDragEnd={() => setDragIdx(null)}
                        className="h-9 grid place-items-center cursor-grab active:cursor-grabbing text-muted-foreground"
                      >
                        <GripVertical className="h-4 w-4" />
                      </button>
                      <Input value={line.time} onChange={(e) => updateScript(i, { time: e.target.value })} className="h-9 text-[11px] px-1.5" />
                      <div className="space-y-1">
                        <Input value={line.caption} onChange={(e) => updateScript(i, { caption: e.target.value })} placeholder="자막" className="h-8 text-xs" />
                        <Input value={line.narration} onChange={(e) => updateScript(i, { narration: e.target.value })} placeholder="나레이션" className="h-8 text-xs" />
                      </div>
                    </div>
                  ))}
                </div>
                <div className="flex gap-2 pt-1">
                  <Button variant="outline" size="sm" className="flex-1" onClick={() => saveMut.mutate()} disabled={saveMut.isPending}>
                    <Save className="h-3 w-3" /> 대본 저장
                  </Button>
                  <Button size="sm" className="flex-1" onClick={() => videoMut.mutate()} disabled={videoMut.isPending}>
                    {videoMut.isPending ? <Loader2 className="h-3 w-3 animate-spin" /> : <Clapperboard className="h-3 w-3" />}{" "}
                    영상 생성
                  </Button>
                </div>
                <p className="text-[11px] text-muted-foreground">대본 수정 후 "대본 저장" → "영상 생성" 순서로 반영됩니다.</p>
              </div>
            )}

            {/* 영상 미리보기 */}
            {videoUrl && (
              <div className="space-y-2">
                <Label>숏폼 미리보기</Label>
                <video
                  key={videoVersion}
                  src={`${videoUrl}?v=${videoVersion}`}
                  controls
                  playsInline
                  className="mx-auto aspect-[9/16] max-h-[420px] rounded-md border bg-black"
                />
              </div>
            )}
          </div>
        </SheetContent>
      </Sheet>
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
