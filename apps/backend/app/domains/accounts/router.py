from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import Principal, client_ip, get_db, get_principal, request_meta
from app.core import ratelimit
from app.domains.accounts import service
from app.domains.merchants.models import Membership, Merchant
from app.domains.platform import outbox

router = APIRouter(tags=["auth"])


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=256)
    full_name: str = Field(min_length=1, max_length=200)
    phone: str | None = Field(default=None, pattern=r"^\+?[0-9 \-]{7,20}$")
    locale: Literal["en", "ne"] = "en"


class UserOut(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    phone: str | None
    locale: str
    email_verified: bool
    mfa_enabled: bool

    @staticmethod
    def of(u: service.User) -> UserOut:
        return UserOut(
            id=u.id,
            email=u.email,
            full_name=u.full_name,
            phone=u.phone,
            locale=u.locale,
            email_verified=u.email_verified_at is not None,
            mfa_enabled=u.mfa_enabled,
        )


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=256)
    device_name: str | None = Field(default=None, max_length=120)


class TokenPairOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    session_id: uuid.UUID


class MfaChallengeOut(BaseModel):
    mfa_required: bool = True
    mfa_token: str


class MfaVerifyIn(BaseModel):
    mfa_token: str
    code: str = Field(min_length=6, max_length=16)


class RefreshIn(BaseModel):
    refresh_token: str = Field(min_length=20, max_length=200)


def _pair(p: service.TokenPair) -> TokenPairOut:
    return TokenPairOut(
        access_token=p.access_token,
        refresh_token=p.refresh_token,
        expires_in=p.expires_in,
        session_id=p.session_id,
    )


@router.post("/auth/register", status_code=201, response_model=UserOut)
def register(body: RegisterIn, request: Request, db: Session = Depends(get_db)) -> UserOut:
    ratelimit.hit(f"register:ip:{client_ip(request)}", limit=10, window_seconds=3600)
    user = service.register(
        db,
        email=body.email,
        password=body.password,
        full_name=body.full_name,
        phone=body.phone,
        locale=body.locale,
        meta=request_meta(request),
    )
    return UserOut.of(user)


@router.post("/auth/login", response_model=TokenPairOut | MfaChallengeOut)
def login(body: LoginIn, request: Request, db: Session = Depends(get_db)) -> TokenPairOut | MfaChallengeOut:
    ratelimit.hit(f"login:ip:{client_ip(request)}", limit=30, window_seconds=60)
    ratelimit.hit(f"login:email:{body.email.lower()}", limit=10, window_seconds=300)
    result = service.login(
        db, email=body.email, password=body.password, device_name=body.device_name, meta=request_meta(request)
    )
    if isinstance(result, service.MfaChallenge):
        return MfaChallengeOut(mfa_token=result.mfa_token)
    return _pair(result)


@router.post("/auth/mfa/verify", response_model=TokenPairOut)
def mfa_verify(body: MfaVerifyIn, request: Request, db: Session = Depends(get_db)) -> TokenPairOut:
    ratelimit.hit(f"mfa:ip:{client_ip(request)}", limit=20, window_seconds=300)
    return _pair(service.verify_mfa(db, mfa_token=body.mfa_token, code=body.code, meta=request_meta(request)))


@router.post("/auth/refresh", response_model=TokenPairOut)
def refresh(body: RefreshIn, request: Request, db: Session = Depends(get_db)) -> TokenPairOut:
    return _pair(service.refresh(db, refresh_token=body.refresh_token, meta=request_meta(request)))


@router.post("/auth/logout", status_code=204)
def logout(body: RefreshIn, request: Request, db: Session = Depends(get_db)) -> Response:
    service.logout(db, refresh_token=body.refresh_token, meta=request_meta(request))
    return Response(status_code=204)


class SessionOut(BaseModel):
    id: uuid.UUID
    device_name: str | None
    ip: str | None
    user_agent: str | None
    created_at: datetime
    last_used_at: datetime
    mfa: bool
    current: bool


@router.get("/auth/sessions")
def sessions(
    p: Principal = Depends(get_principal), db: Session = Depends(get_db)
) -> dict[str, list[SessionOut]]:
    rows = service.list_sessions(db, p.user.id)
    return {
        "items": [
            SessionOut(
                id=s.id,
                device_name=s.device_name,
                ip=s.ip,
                user_agent=s.user_agent,
                created_at=s.created_at,
                last_used_at=s.last_used_at,
                mfa="mfa" in s.amr,
                current=s.id == p.session.id,
            )
            for s in rows
        ]
    }


@router.delete("/auth/sessions/{session_id}", status_code=204)
def revoke_session(
    session_id: uuid.UUID,
    request: Request,
    p: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
) -> Response:
    service.revoke_session(db, p.user, session_id, request_meta(request))
    return Response(status_code=204)


@router.post("/auth/sessions/revoke-all", status_code=204)
def revoke_all(
    request: Request, p: Principal = Depends(get_principal), db: Session = Depends(get_db)
) -> Response:
    service.revoke_all_other_sessions(db, p.user, p.session.id, request_meta(request))
    return Response(status_code=204)


class TotpSetupOut(BaseModel):
    secret: str
    otpauth_uri: str


class CodeIn(BaseModel):
    code: str = Field(min_length=6, max_length=8, pattern=r"^[0-9]+$")


class DisableMfaIn(CodeIn):
    password: str = Field(min_length=1, max_length=256)


@router.post("/auth/mfa/totp/setup", response_model=TotpSetupOut)
def totp_setup(p: Principal = Depends(get_principal), db: Session = Depends(get_db)) -> TotpSetupOut:
    secret, uri = service.totp_setup(db, p.user)
    return TotpSetupOut(secret=secret, otpauth_uri=uri)


@router.post("/auth/mfa/totp/enable")
def totp_enable(
    body: CodeIn, request: Request, p: Principal = Depends(get_principal), db: Session = Depends(get_db)
) -> dict[str, list[str]]:
    return {"recovery_codes": service.totp_enable(db, p.user, body.code, request_meta(request))}


@router.post("/auth/mfa/totp/disable", status_code=204)
def totp_disable(
    body: DisableMfaIn, request: Request, p: Principal = Depends(get_principal), db: Session = Depends(get_db)
) -> Response:
    service.totp_disable(db, p.user, body.code, body.password, request_meta(request))
    return Response(status_code=204)


@router.post("/auth/verify-email/request", status_code=202)
def verify_email_request(p: Principal = Depends(get_principal), db: Session = Depends(get_db)) -> Response:
    ratelimit.hit(f"verify-email:{p.user.id}", limit=5, window_seconds=3600)
    if p.user.email_verified_at is None:
        outbox.publish(
            db,
            event_type="accounts.email_verification_requested",
            aggregate_type="user",
            aggregate_id=p.user.id,
            merchant_id=None,
            payload={"user_id": str(p.user.id)},
        )
    return Response(status_code=202)


class TokenIn(BaseModel):
    token: str = Field(min_length=20, max_length=200)


@router.post("/auth/verify-email/confirm", status_code=204)
def verify_email_confirm(body: TokenIn, request: Request, db: Session = Depends(get_db)) -> Response:
    service.confirm_email(db, body.token, request_meta(request))
    return Response(status_code=204)


# ----------------------------------------------------------------------------- me
class MerchantRef(BaseModel):
    id: uuid.UUID
    name: str
    slug: str


class MembershipOut(BaseModel):
    merchant: MerchantRef
    role: str
    status: str


class MeOut(BaseModel):
    user: UserOut
    memberships: list[MembershipOut]


@router.get("/me", response_model=MeOut, tags=["me"])
def me(p: Principal = Depends(get_principal), db: Session = Depends(get_db)) -> MeOut:
    rows = db.execute(
        select(Membership, Merchant)
        .join(Merchant, Merchant.id == Membership.merchant_id)
        .where(Membership.user_id == p.user.id, Membership.status == "active")
        .order_by(Merchant.name)
    ).all()
    return MeOut(
        user=UserOut.of(p.user),
        memberships=[
            MembershipOut(
                merchant=MerchantRef(id=mc.id, name=mc.name, slug=mc.slug), role=m.role, status=m.status
            )
            for m, mc in rows
        ],
    )


class MePatch(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=200)
    phone: str | None = Field(default=None, pattern=r"^\+?[0-9 \-]{7,20}$")
    locale: Literal["en", "ne"] | None = None


@router.patch("/me", response_model=UserOut, tags=["me"])
def patch_me(
    body: MePatch, request: Request, p: Principal = Depends(get_principal), db: Session = Depends(get_db)
) -> UserOut:
    from app.domains.audit import service as audit

    before = {"full_name": p.user.full_name, "phone": p.user.phone, "locale": p.user.locale}
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(p.user, k, v)
    changes = audit.diff(before, {k: getattr(p.user, k) for k in before})
    if changes:
        audit.record(
            db,
            action="accounts.profile_updated",
            resource_type="user",
            resource_id=p.user.id,
            actor=p.actor,
            merchant_id=None,
            meta=request_meta(request),
            changes=changes,
        )
    return UserOut.of(p.user)
