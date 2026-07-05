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

export interface GeneratePayload {
  keywords: string[];
  tone: string;
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

export async function pingBackend(): Promise<boolean> {
  try {
    await api.get("/", { timeout: 2000 });
    return true;
  } catch {
    return false;
  }
}
