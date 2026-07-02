from sqlite3 import IntegrityError

from fastapi import Depends
from sqlalchemy import insert, select, or_, and_, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import (
    DBCreateRequestError, AppError, DBGetRecordsError,
    DBSearchRecordsError, DBNotFoundError, DBConflictError,
    DBError, DBDeleteRecordsError, get_db
)
from app.enums import Status, Role
from app.models import Request
from app.schemas import CreateReqShem, Filters, Search, UpdateParams



class RequestRepo:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_request(self, request: CreateReqShem, user_id: int):
        data = request.model_dump(exclude_unset=True)
        data['created_by'] = user_id
        async with self.db.begin():
            try:
                result = await self.db.execute(
                    insert(Request)
                    .values(**data)
                    .returning(Request.id)
                )
                inserted = result.scalar_one_or_none()
                if inserted is None:
                    raise DBCreateRequestError('Не возможно создать заявку')
                return inserted
            except IntegrityError as e:
                raise AppError(f'Ошибка создания заявки: {e}')

    async def get_requests(self, user_id: int, filters: Filters, role: Role):
        async with self.db.begin():
            wheres = []
            orders = []

            if role == Role.user:
                wheres.append(Request.created_by == user_id)
            if filters.priority is not None:
                wheres.append(Request.priority == filters.priority)
            if filters.status is not None:
                wheres.append(Request.status == filters.status)

            if filters.sort_date:
                orders.append(Request.created_at.desc())
            if filters.sort_priority:
                orders.append(Request.priority.desc())
                if not filters.sort_date:
                    orders.append(Request.created_at.desc())

            stmt = select(Request)
            if wheres:
                stmt = stmt.where(*wheres)
            if orders:
                stmt = stmt.order_by(*orders)

            stmt = stmt.offset((filters.page - 1) * filters.limit).limit(filters.limit)
            try:
                result = await self.db.execute(stmt)
                return result.scalars().all()
            except IntegrityError as e:
                raise DBGetRecordsError(e)

    async def search_requests(self, user_id: int, search: Search, role: Role):
        async with self.db.begin():
            wheres = []
            conditions = []

            if role == Role.user:
                wheres.append(Request.created_by == user_id)

            if search.title:
                conditions.append(Request.title.ilike(f"%{search.title}%"))
            if search.description:
                conditions.append(Request.description.ilike(f"%{search.description}%"))

            wheres.append(or_(*conditions))
            try:
                result = await self.db.execute(
                    select(Request)
                    .where(*wheres)
                )
                return result.scalars().all()
            except IntegrityError as e:
                raise DBSearchRecordsError(e)

    async def update_status(self, user_id: int, target: UpdateParams, role: Role):
        async with self.db.begin():
            wheres = []
            if role == Role.user:
                wheres.append(Request.created_by == user_id)
            wheres.append(Request.id == target.req_id)
            try:
                resul = await self.db.execute(
                    select(Request).where(*wheres)
                )

                data = resul.scalar_one_or_none()
                if data is None:
                    raise DBNotFoundError('Record not found')
                if data.status == Status.done:
                    raise DBConflictError('Status already done')

                res = await self.db.execute(
                    update(Request.status)
                    .where(Request.id == target.req_id)
                    .values(target.status)
                    .returning(Request.id, Request.status)
                )
                result = res.scalar_one_or_none()
                if result is None:
                    raise DBError('Failed to update status')
                return result
            except IntegrityError as e:
                raise DBError(f'Failed update request status: {e}')

    async def delete_request(self, req_id: int):
        async with self.db.begin():
            try:
                request = await self.db.execute(
                    select(Request)
                    .where(Request.id == req_id)
                )
                data = request.scalar_one_or_none()
                if data is None:
                    raise DBNotFoundError('Record not found')
                if data.status == Status.done:
                    raise DBConflictError('Status is done')

                result = await self.db.execute(
                    delete(Request)
                    .where(Request.id == req_id)
                    .returning(Request.id)
                )
                res = result.scalar_one_or_none()
                if res is None:
                    raise DBDeleteRecordsError('Record not found')
            except IntegrityError as e:
                raise DBError(f'Failed delete request status: {e}')


async def get_request_repo(db: AsyncSession = Depends(get_db)):
    return RequestRepo(db=db)
