from fastapi import APIRouter, Depends, HTTPException, status

from app.core import DBConflictError, DBError, DBNotFoundError
from app.core.security import get_current_user
from app.enums import Role
from app.models import User as DBUser
from app.repositories import RequestRepo, get_request_repo
from app.schemas import CreateReqShem, Filters, RequestListOut, RequestOut, Search, UpdateParams

router = APIRouter(prefix="/requests", tags=["requests"])


def _raise_http_from_app_error(exc: Exception) -> None:
    if isinstance(exc, DBNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message) from exc

    if isinstance(exc, DBConflictError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.message) from exc

    if isinstance(exc, DBError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message) from exc

    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Внутренняя ошибка сервера",
    ) from exc


@router.post("", response_model=RequestOut, status_code=status.HTTP_201_CREATED)
async def create_request(
    payload: CreateReqShem,
    current_user: DBUser = Depends(get_current_user),
    request_repo: RequestRepo = Depends(get_request_repo),
) -> RequestOut:
    try:
        return await request_repo.create_request(payload, current_user.id)
    except Exception as exc:
        _raise_http_from_app_error(exc)


@router.get("", response_model=RequestListOut)
async def list_requests(
    filters: Filters = Depends(),
    search: Search = Depends(),
    current_user: DBUser = Depends(get_current_user),
    request_repo: RequestRepo = Depends(get_request_repo),
) -> RequestListOut:
    try:
        items, total = await request_repo.get_requests(
            user_id=current_user.id,
            filters=filters,
            search=search,
            role=current_user.role,
        )
        return RequestListOut(
            items=items,
            page=filters.page,
            limit=filters.limit,
            total=total,
        )
    except Exception as exc:
        _raise_http_from_app_error(exc)


@router.patch("/status", response_model=RequestOut)
async def update_request_status(
    payload: UpdateParams,
    current_user: DBUser = Depends(get_current_user),
    request_repo: RequestRepo = Depends(get_request_repo),
) -> RequestOut:
    try:
        return await request_repo.update_status(
            user_id=current_user.id,
            target=payload,
            role=current_user.role,
        )
    except Exception as exc:
        _raise_http_from_app_error(exc)


@router.delete("/{request_id}")
async def delete_request(
    request_id: int,
    current_user: DBUser = Depends(get_current_user),
    request_repo: RequestRepo = Depends(get_request_repo),
) -> dict[str, int]:
    if current_user.role != Role.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Удалять заявки может только админ",
        )

    try:
        deleted_id = await request_repo.delete_request(request_id)
        return {"deleted_id": deleted_id}
    except Exception as exc:
        _raise_http_from_app_error(exc)
