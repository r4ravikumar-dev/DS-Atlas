from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from ..core.logging import request_id_var
from ..models import AuditEvent


def audit(db: Session, user_id, action: str, target_type: str | None = None, target_id: Any = None, **details: Any) -> None:
    db.add(AuditEvent(user_id=user_id, action=action, target_type=target_type, target_id=str(target_id) if target_id is not None else None,
                      details=details, request_id=request_id_var.get()))
