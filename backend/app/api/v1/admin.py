"""Admin portal: customer + user management. Scoped to the caller's customer."""
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.rbac import require_admin
from app.core.security import hash_password
from app.db.models import AuditAction, Customer, CustomerUser, User
from app.db.session import get_db
from app.deps import AuthenticatedUser
from app.schemas.admin import CustomerOut, CustomerUpdate, UserCreate, UserOut, UserUpdate
from app.services import audit

router = APIRouter()


@router.get("/customer", response_model=CustomerOut)
def my_customer(
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_admin()),
):
    cust = db.get(Customer, current_user.customer_id)
    if not cust:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Customer not found")
    return cust


@router.patch("/customer", response_model=CustomerOut)
def update_customer(
    payload: CustomerUpdate,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_admin()),
):
    cust = db.get(Customer, current_user.customer_id)
    if not cust:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Customer not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(cust, k, v)
    audit.record(db, action=AuditAction.ADMIN_CUSTOMER_UPDATED,
                 customer_id=cust.id, user_id=current_user.id,
                 context={"fields": list(payload.model_dump(exclude_unset=True).keys())})
    db.commit(); db.refresh(cust)
    return cust


@router.get("/users", response_model=List[UserOut])
def list_users(
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_admin()),
):
    rows = list(db.scalars(
        select(User).join(CustomerUser, CustomerUser.user_id == User.id)
        .where(CustomerUser.customer_id == current_user.customer_id)
    ))
    out: list[UserOut] = []
    for u in rows:
        link = next((cu for cu in u.customer_users if cu.customer_id == current_user.customer_id), None)
        out.append(UserOut(
            id=u.id, email=u.email, full_name=u.full_name,
            is_active=u.is_active, is_superadmin=u.is_superadmin,
            mfa_enabled=u.mfa_enabled, last_login_at=u.last_login_at,
            role=(link.role if link else None),
        ))
    return out


@router.post("/users", response_model=UserOut, status_code=201)
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_admin()),
):
    if db.scalar(select(User).where(User.email == payload.email.lower())):
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already in use")
    u = User(
        email=payload.email.lower(), full_name=payload.full_name,
        password_hash=hash_password(payload.password), is_active=True,
    )
    db.add(u); db.flush()
    db.add(CustomerUser(customer_id=current_user.customer_id, user_id=u.id, role=payload.role))
    audit.record(db, action=AuditAction.ADMIN_USER_CREATED,
                 customer_id=current_user.customer_id, user_id=current_user.id,
                 context={"target_user_id": str(u.id), "role": payload.role})
    db.commit(); db.refresh(u)
    return UserOut(
        id=u.id, email=u.email, full_name=u.full_name,
        is_active=u.is_active, is_superadmin=u.is_superadmin,
        mfa_enabled=u.mfa_enabled, last_login_at=u.last_login_at, role=payload.role,
    )


@router.patch("/users/{user_id}", response_model=UserOut)
def update_user(
    user_id: UUID,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_admin()),
):
    link = db.scalar(
        select(CustomerUser)
        .where(CustomerUser.user_id == user_id, CustomerUser.customer_id == current_user.customer_id)
    )
    if not link:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not in your customer")
    u = db.get(User, user_id)

    data = payload.model_dump(exclude_unset=True)
    if "role" in data:
        link.role = data.pop("role")
    for k, v in data.items():
        setattr(u, k, v)

    audit.record(db, action=AuditAction.ADMIN_USER_UPDATED,
                 customer_id=current_user.customer_id, user_id=current_user.id,
                 context={"target_user_id": str(u.id), "fields": list(payload.model_dump(exclude_unset=True).keys())})
    db.commit(); db.refresh(u)
    return UserOut(
        id=u.id, email=u.email, full_name=u.full_name,
        is_active=u.is_active, is_superadmin=u.is_superadmin,
        mfa_enabled=u.mfa_enabled, last_login_at=u.last_login_at, role=link.role,
    )


@router.delete("/users/{user_id}", status_code=204)
def delete_user(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_admin()),
):
    if user_id == current_user.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Cannot delete yourself")
    link = db.scalar(
        select(CustomerUser)
        .where(CustomerUser.user_id == user_id, CustomerUser.customer_id == current_user.customer_id)
    )
    if not link:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not in your customer")
    db.delete(link)
    audit.record(db, action=AuditAction.ADMIN_USER_DELETED,
                 customer_id=current_user.customer_id, user_id=current_user.id,
                 context={"target_user_id": str(user_id)})
    db.commit()
    return None
