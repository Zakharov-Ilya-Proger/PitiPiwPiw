from datetime import datetime

from fastapi import Depends
from sqlalchemy import case, func, or_, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import (
    DBCreateRequestError,
    DBDeleteRecordsError,
    DBError,
    DBGetRecordsError,
    DBNotFoundError,
    DBConflictError,
    get_db,
)
from app.enums import Priority, Role, Status
from app.models import Request
from app.schemas import CreateReqShem, Filters, Search, UpdateParams


class RequestRepo:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_request(self, request: CreateReqShem, user_id: int) -> Request:
        data = request.model_dump(exclude_unset=True)
        data["created_by"] = user_id

        db_request = Request(**data)
        self.db.add(db_request)

        try:
            await self.db.commit()
            await self.db.refresh(db_request)
            return db_request
        except IntegrityError as exc:
            await self.db.rollback()
            raise DBCreateRequestError(f"Ошибка создания заявки: {exc}") from exc
        except (SQLAlchemyError, ValueError) as exc:
            await self.db.rollback()
            raise DBCreateRequestError(f"Ошибка создания заявки: {exc}") from exc

    def _where_conditions(
        self,
        *,
        user_id: int,
        filters: Filters,
        search: Search | None,
        role: Role,
    ) -> list:
        conditions = []

        if role == Role.user:
            conditions.append(Request.created_by == user_id)

        if filters.status is not None:
            conditions.append(Request.status == filters.status)

        if filters.priority is not None:
            conditions.append(Request.priority == filters.priority)

        search_conditions = []
        if search is not None:
            if search.title:
                search_conditions.append(Request.title.ilike(f"%{search.title}%"))
            if search.description:
                search_conditions.append(Request.description.ilike(f"%{search.description}%"))

        if search_conditions:
            conditions.append(or_(*search_conditions))

        return conditions

    def _order_by(self, filters: Filters) -> list:
        orders = []

        if filters.sort_priority:
            priority_rank = case(
                (Request.priority == Priority.high, 3),
                (Request.priority == Priority.normal, 2),
                (Request.priority == Priority.low, 1),
                else_=0,
            )
            orders.append(priority_rank.desc())

        if filters.sort_date:
            orders.append(Request.created_at.desc())

        if not orders:
            orders.append(Request.created_at.desc())

        return orders

    async def get_requests(
        self,
        user_id: int,
        filters: Filters,
        role: Role,
        search: Search | None = None,
    ) -> tuple[list[Request], int]:
        conditions = self._where_conditions(
            user_id=user_id,
            filters=filters,
            search=search,
            role=role,
        )
        orders = self._order_by(filters)

        page = max(filters.page, 1)
        limit = max(min(filters.limit, 100), 1)
        offset = (page - 1) * limit

        stmt = select(Request)
        count_stmt = select(func.count()).select_from(Request)

        if conditions:
            stmt = stmt.where(*conditions)
            count_stmt = count_stmt.where(*conditions)

        stmt = stmt.order_by(*orders).offset(offset).limit(limit)

        try:
            result = await self.db.execute(stmt)
            total_result = await self.db.execute(count_stmt)
            return list(result.scalars().all()), int(total_result.scalar_one())
        except SQLAlchemyError as exc:
            raise DBGetRecordsError(f"Ошибка получения заявок: {exc}") from exc

    async def search_requests(self, user_id: int, search: Search, role: Role) -> tuple[list[Request], int]:
        filters = Filters(page=1, limit=100, sort_date=True, sort_priority=False)
        return await self.get_requests(user_id=user_id, filters=filters, search=search, role=role)

    async def update_status(self, user_id: int, target: UpdateParams, role: Role) -> Request:
        conditions = [Request.id == target.req_id]
        if role == Role.user:
            conditions.append(Request.created_by == user_id)

        try:
            result = await self.db.execute(select(Request).where(*conditions))
            db_request = result.scalar_one_or_none()

            if db_request is None:
                raise DBNotFoundError("Заявка не найдена")

            if db_request.status == Status.done:
                raise DBConflictError("Заявку в статусе done нельзя редактировать")

            db_request.status = target.target_status
            db_request.updated_at = datetime.utcnow()

            await self.db.commit()
            await self.db.refresh(db_request)
            return db_request
        except (DBNotFoundError, DBConflictError):
            await self.db.rollback()
            raise
        except SQLAlchemyError as exc:
            await self.db.rollback()
            raise DBError(f"Ошибка изменения статуса заявки: {exc}") from exc

    async def delete_request(self, req_id: int) -> int:
        try:
            result = await self.db.execute(select(Request).where(Request.id == req_id))
            db_request = result.scalar_one_or_none()

            if db_request is None:
                raise DBNotFoundError("Заявка не найдена")

            if db_request.status == Status.done:
                raise DBConflictError("Заявку в статусе done нельзя удалить")

            deleted_id = db_request.id
            await self.db.delete(db_request)
            await self.db.commit()
            return deleted_id
        except (DBNotFoundError, DBConflictError):
            await self.db.rollback()
            raise
        except SQLAlchemyError as exc:
            await self.db.rollback()
            raise DBDeleteRecordsError(f"Ошибка удаления заявки: {exc}") from exc


async def get_request_repo(db: AsyncSession = Depends(get_db)) -> RequestRepo:
    return RequestRepo(db=db)
