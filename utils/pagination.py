from flask import request


def paginate_query(query, default_page=1, default_per_page=20, max_per_page=100):
    try:
        page = max(1, request.args.get("page", default_page, type=int) or default_page)
        per_page = request.args.get("per_page", default_per_page, type=int) or default_per_page
    except (TypeError, ValueError):
        page = default_page
        per_page = default_per_page

    per_page = max(1, min(per_page, max_per_page))

    pagination = query.paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )

    return {
        "data": pagination.items,
        "pagination": {
            "page": pagination.page,
            "per_page": pagination.per_page,
            "total": pagination.total,
            "pages": pagination.pages,
            "has_next": pagination.has_next,
            "has_prev": pagination.has_prev,
        }
    }
