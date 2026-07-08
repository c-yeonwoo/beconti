import axios from "axios";

export const API_BASE_URL = "http://localhost:8000";

export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 60000,
});

export type Platform = "naver_blog" | "naver_clip" | "instagram";
export type PublishStatus = "idle" | "queued" | "success" | "failed";

export interface ScriptLine {
  time: string;
  caption: string;
  narration: string;
}

export interface GeneratedContent {
  id: string;
  title: string;
  body: string;
  videoUrl?: string;
  script: ScriptLine[];
  createdAt: string;
  platformStatus: Record<Platform, PublishStatus>;
}

export type ContentType = "place_review" | "product_review" | "vlog";

export const CATEGORIES = [
  "맛집",
  "카페",
  "뷰티",
  "패션",
  "여행",
  "리빙/홈",
  "제품",
  "반려동물",
  "문화/여가",
  "건강/운동",
  "기타",
];

export type ScriptStyle = "polite" | "cute" | "energetic" | "broadcast";

export const SCRIPT_STYLES: { value: ScriptStyle; label: string }[] = [
  { value: "polite", label: "존댓말 (깔끔한 리뷰)" },
  { value: "cute", label: "반말·귀여운 브이로그" },
  { value: "energetic", label: "활기찬 반말 (텐션↑)" },
  { value: "broadcast", label: "맛집 탐방 리포터 (VJ특공대 톤)" },
];

export type CaptionStyle = "basic" | "yellow" | "neon";

export const CAPTION_STYLES: { value: CaptionStyle; label: string }[] = [
  { value: "basic", label: "기본 (흰색+박스)" },
  { value: "yellow", label: "노랑 굵게 (예능체)" },
  { value: "neon", label: "네온 (글로우)" },
];

export interface GeneratePayload {
  keywords: string[];
  category: string;
  contentType: ContentType;
  guideline: string; // 비우면 백엔드가 유형별 기본 가이드라인 사용
  scriptStyle: ScriptStyle; // 숏폼 대본 말투
  captionStyle: CaptionStyle; // 숏폼 자막 스타일
  requiredHashtags: string[];
  placeName: string; // 매장명(상호) — 네이버 장소 카드(지도) 삽입용
  placeUrl: string; // (옵션) 네이버 지도 링크 — 있으면 우선
  mediaIds: string[];
}

export async function getDefaults() {
  const { data } = await api.get("/api/defaults");
  return data as { blog: string; video: string };
}

export async function uploadMedia(files: File[]) {
  const form = new FormData();
  files.forEach((f) => form.append("files", f));
  const { data } = await api.post("/api/upload", form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data as { mediaIds: string[] };
}

export async function generateContent(payload: GeneratePayload) {
  const { data } = await api.post("/api/generate", payload);
  return data as GeneratedContent;
}

export async function publishContent(payload: {
  contentId: string;
  platforms: Platform[];
}) {
  const { data } = await api.post("/api/publish", payload);
  return data as { ok: boolean };
}

export async function listContent() {
  const { data } = await api.get("/api/content");
  return data as GeneratedContent[];
}

export async function getContentById(id: string) {
  const { data } = await api.get(`/api/content/${id}`);
  return data as GeneratedContent;
}

export async function updateContent(
  id: string,
  patch: { title: string; body: string; script: ScriptLine[] },
) {
  const { data } = await api.patch(`/api/content/${id}`, patch);
  return data as GeneratedContent;
}

export interface ContentSettings {
  keywords: string[];
  category: string;
  contentType: ContentType;
  guideline: string;
  scriptStyle: ScriptStyle;
  captionStyle: CaptionStyle;
  requiredHashtags: string[];
  placeName: string;
  placeUrl: string;
  media: { mediaId: string; url: string }[];
}

export async function getContentSettings(id: string) {
  const { data } = await api.get(`/api/content/${id}/settings`);
  return data as ContentSettings;
}

export async function regenerateContent(id: string, payload: GeneratePayload) {
  const { data } = await api.post(`/api/content/${id}/regenerate`, payload, {
    timeout: 120000,
  });
  return data as GeneratedContent;
}

export interface ComplianceCheck {
  label: string;
  ok: boolean;
}
export interface ComplianceResult {
  checks: ComplianceCheck[];
  passed: number;
  total: number;
}

export async function checkCompliance(payload: {
  body: string;
  keywords: string[];
  requiredHashtags: string[];
  guideline: string;
  photoCount: number;
}) {
  const { data } = await api.post("/api/compliance", payload);
  return data as ComplianceResult;
}

export async function makeVideo(contentId: string) {
  const { data } = await api.post(
    `/api/video/${contentId}`,
    {},
    { timeout: 180000 }, // 렌더에 시간 소요
  );
  return data as GeneratedContent;
}

export async function pingBackend(): Promise<boolean> {
  try {
    await api.get("/", { timeout: 2000 });
    return true;
  } catch {
    return false;
  }
}
