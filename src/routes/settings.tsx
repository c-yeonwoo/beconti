import { createFileRoute } from "@tanstack/react-router";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { API_BASE_URL } from "@/lib/api";

export const Route = createFileRoute("/settings")({
  head: () => ({
    meta: [
      { title: "세팅 · beconti" },
      { name: "description", content: "백엔드 및 플랫폼 계정 연결 상태" },
    ],
  }),
  component: SettingsPage,
});

const accounts = [
  { name: "네이버 블로그", type: "Playwright 세션", status: "unknown" },
  { name: "네이버 클립", type: "Playwright 세션", status: "unknown" },
  { name: "워드프레스", type: "REST API", status: "unknown" },
  { name: "인스타그램", type: "Meta Graph API", status: "unknown" },
];

function SettingsPage() {
  return (
    <div className="p-6 space-y-6 max-w-3xl">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">세팅</h1>
        <p className="text-sm text-muted-foreground">
          백엔드와 배포 플랫폼 연결 정보를 확인합니다.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">백엔드</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="space-y-2">
            <Label>API Base URL</Label>
            <Input value={API_BASE_URL} readOnly />
            <p className="text-xs text-muted-foreground">
              FastAPI 서버 주소. 변경 시 <code>src/lib/api.ts</code>의{" "}
              <code>API_BASE_URL</code>을 수정하세요.
            </p>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">플랫폼 계정</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="divide-y">
            {accounts.map((a) => (
              <div
                key={a.name}
                className="flex items-center justify-between py-3"
              >
                <div>
                  <div className="text-sm font-medium">{a.name}</div>
                  <div className="text-xs text-muted-foreground">{a.type}</div>
                </div>
                <Badge variant="secondary">확인 필요</Badge>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
