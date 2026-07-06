"""캠페인 준수 체크 엔드포인트 (본문 편집 후에도 재검사 가능)."""

from fastapi import APIRouter

from ..models import CompliancePayload, ComplianceResult
from ..services.compliance import check_compliance

router = APIRouter(prefix="/api", tags=["compliance"])


@router.post("/compliance", response_model=ComplianceResult)
def compliance(payload: CompliancePayload) -> ComplianceResult:
    raw = check_compliance(
        payload.body,
        payload.keywords,
        payload.requiredHashtags,
        payload.guideline,
        payload.photoCount,
    )
    passed = sum(1 for c in raw if c["ok"])
    return ComplianceResult(checks=raw, passed=passed, total=len(raw))
