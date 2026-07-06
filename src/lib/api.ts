import axios from "axios";

export const API_BASE_URL = "http://localhost:8000";

export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 60000,
});

export type Platform = "naver_blog" | "naver_clip" | "wordpress" | "instagram";
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

export interface GeneratePayload {
  keywords: string[];
  category: string;
  contentType: ContentType;
  guideline: string; // 비우면 백엔드가 유형별 기본 가이드라인 사용
  requiredHashtags: string[];
  placeName: string; // 매장명(상호) — 네이버 장소 카드(지도) 삽입용
  mediaIds: string[];
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
