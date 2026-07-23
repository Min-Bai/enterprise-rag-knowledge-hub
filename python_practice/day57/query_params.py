from fastapi import HTTPException, Query
from pydantic import BaseModel


class PaginationParams(BaseModel):
    limit: int
    offset: int
    page: int | None
    page_size: int | None


def get_pagination_params(
    limit: int = Query(default=10, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    page: int | None = Query(default=None, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
):
    if page is not None:
        if offset != 0:
            raise HTTPException(
                status_code=400,
                detail="cannot use page and offset together",
            )

        limit = page_size
        offset = (page - 1) * page_size

    return PaginationParams(
        limit=limit,
        offset=offset,
        page=page,
        page_size=page_size if page is not None else None,
    )
