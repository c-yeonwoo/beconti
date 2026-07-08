import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useCallback, useState } from "react";
import { toast } from "sonner";
import { Upload, X, Sparkles, Loader2 } from "lucide-react";
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
  getDefaults,
  CATEGORIES,
  type ContentType,
} from "@/lib/api";

export const Route = createFileRoute("/create")({
  head: () => ({
    meta: [
      { title: "콘텐츠 생성 · beconti" },
      { name: "description", content: "미디어를 업로드해 블로그 글을 생성" },
    ],
  }),
  component: CreatePage,
});

interface MediaItem {
  file: File;
  url: string;
  isVideo: boolean;
}

function CreatePage() {
  const navigate = useNavigate();
  const [media, setMedia] = useState<MediaItem[]>([]);
  const [keywordInput, setKeywordInput] = useState("");
  const [keywords, setKeywords] = useState<string[]>([]);
  const [category, setCategory] = useState("");
  const [contentType, setContentType] = useState<ContentType>("place_review");
  const [placeName, setPlaceName] = useState("");
  const [placeUrl, setPlaceUrl] = useState("");
  const [hashtagInput, setHashtagInput] = useState("");
  const [hashtags, setHashtags] = useState<string[]>([]);
  const [blogGuideline, setBlogGuideline] = useState("");
  const [dragging, setDragging] = useState(false);

  const defaultsQ = useQuery({ queryKey: ["defaults"], queryFn: getDefaults, staleTime: Infinity });

  const mutation = useMutation({
    mutationFn: async () => {
      const { mediaIds } = await uploadMedia(media.map((m) => m.file));
      return generateContent({
        keywords,
        category,
        contentType,
        blogGuideline,
        shortsGuideline: "",
        scriptStyle: "polite",
        captionStyle: "basic",
        requiredHashtags: hashtags,
        placeName,
        placeUrl,
        mediaIds,
      });
    },
    onSuccess: (data) => {
      toast.success("블로그 글 생성 완료", { description: "이어서 편집·숏폼 제작을 할 수 있어요." });
      navigate({ to: "/content/$id", params: { id: data.id } });
    },
    onError: (err: Error) => {
      toast.error("생성 실패", {
        description: err.message + " · localhost:8000 백엔드 확인",
      });
    },
  });

  const addFiles = useCallback((files: FileList | File[]) => {
    const arr = Array.from(files);
    setMedia((prev) => [
      ...prev,
      ...arr.map((f) => ({ file: f, url: URL.createObjectURL(f), isVideo: f.type.startsWith("video/") })),
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
    if (!k || keywords.includes(k)) return;
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
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">콘텐츠 생성</h1>
        <p className="text-sm text-muted-foreground">
          사진·영상과 키워드를 넣으면 블로그 글을 만듭니다. 숏폼은 생성 후 상세에서 선택적으로.
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="text-base">미디어 업로드</CardTitle>
          </CardHeader>
          <CardContent>
            <label
              onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
              onDragLeave={() => setDragging(false)}
              onDrop={(e) => { e.preventDefault(); setDragging(false); addFiles(e.dataTransfer.files); }}
              className={cn(
                "flex flex-col items-center justify-center rounded-lg border-2 border-dashed p-10 cursor-pointer transition-colors",
                dragging ? "border-primary bg-primary/5" : "border-border hover:bg-muted/40",
              )}
            >
              <Upload className="h-8 w-8 text-muted-foreground" />
              <p className="mt-3 text-sm font-medium">이미지/영상 파일을 여기에 드롭하세요</p>
              <p className="text-xs text-muted-foreground">또는 클릭해서 선택 (다중 선택 가능)</p>
              <input type="file" multiple accept="image/*,video/*" className="hidden"
                onChange={(e) => e.target.files && addFiles(e.target.files)} />
            </label>

            {media.length > 0 && (
              <div className="mt-4 grid grid-cols-3 md:grid-cols-4 gap-3">
                {media.map((m, i) => (
                  <div key={i} className="relative group aspect-square rounded-md overflow-hidden border bg-muted">
                    {m.isVideo ? (
                      <video src={m.url} className="h-full w-full object-cover" />
                    ) : (
                      <img src={m.url} alt="" className="h-full w-full object-cover" />
                    )}
                    <button onClick={() => removeMedia(i)}
                      className="absolute top-1 right-1 h-6 w-6 rounded-full bg-background/90 grid place-items-center opacity-0 group-hover:opacity-100 transition">
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
                <Input value={keywordInput} placeholder="예: 성수동 카페"
                  onChange={(e) => setKeywordInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.nativeEvent.isComposing && e.keyCode !== 229) {
                      e.preventDefault(); addKeyword();
                    }
                  }} />
                <Button type="button" variant="outline" onClick={addKeyword}>추가</Button>
              </div>
              <div className="flex flex-wrap gap-1.5 pt-1">
                {keywords.map((k) => (
                  <Badge key={k} variant="secondary" className="cursor-pointer" onClick={() => setKeywords(keywords.filter((x) => x !== k))}>
                    {k} <X className="h-3 w-3 ml-1" />
                  </Badge>
                ))}
              </div>
            </div>

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

            <div className="space-y-2">
              <Label>필수 해시태그</Label>
              <div className="flex gap-2">
                <Input value={hashtagInput} placeholder="예: 성수동카페"
                  onChange={(e) => setHashtagInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.nativeEvent.isComposing && e.keyCode !== 229) {
                      e.preventDefault(); addHashtag();
                    }
                  }} />
                <Button type="button" variant="outline" onClick={addHashtag}>추가</Button>
              </div>
              <div className="flex flex-wrap gap-1.5 pt-1">
                {hashtags.map((h) => (
                  <Badge key={h} variant="secondary" className="cursor-pointer" onClick={() => setHashtags(hashtags.filter((x) => x !== h))}>
                    {h} <X className="h-3 w-3 ml-1" />
                  </Badge>
                ))}
              </div>
            </div>

            <div className="space-y-2">
              <Label>매장명 (지도 첨부용, 선택)</Label>
              <Input value={placeName} placeholder="예: 스타벅스 강남대로점" onChange={(e) => setPlaceName(e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label>네이버 지도 링크 (선택)</Label>
              <Input value={placeUrl} placeholder="링크 있으면 우선, 없으면 매장명 검색" onChange={(e) => setPlaceUrl(e.target.value)} />
            </div>

            <div className="space-y-2">
              <Label>블로그 가이드라인</Label>
              <Textarea value={blogGuideline} placeholder={defaultsQ.data?.blog ?? "체험단 가이드라인을 붙여넣으세요 (비우면 기본 규칙)"}
                onChange={(e) => setBlogGuideline(e.target.value)} className="min-h-[120px] text-sm" />
              <p className="text-xs text-muted-foreground">숏폼 대본은 생성 후 상세에서 따로 만들 수 있어요.</p>
            </div>

            <Button className="w-full" disabled={!canGenerate || mutation.isPending} onClick={() => mutation.mutate()}>
              {mutation.isPending ? (
                <><Loader2 className="h-4 w-4 animate-spin" /> 생성 중...</>
              ) : (
                <><Sparkles className="h-4 w-4" /> 블로그 글 생성</>
              )}
            </Button>
            {!canGenerate && (
              <p className="text-xs text-muted-foreground">미디어와 키워드를 하나 이상 추가해 주세요.</p>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
