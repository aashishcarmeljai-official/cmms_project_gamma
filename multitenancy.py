from flask_login import current_user
from sqlalchemy.orm import Query


def filter_by_company(query: Query, model=None, company_id=None):
    """
    Filters a SQLAlchemy query to only include records for the current user's company.
    Optionally, a specific company_id can be provided (e.g., for admin actions).
    """
    if company_id is None:
        if hasattr(current_user, 'company_id'):
            company_id = current_user.company_id
        else:
            raise Exception("Current user does not have a company_id attribute.")
    if model is not None:
        return query.filter(getattr(model, 'company_id') == company_id)
    # If model is not provided, assume query is already model-scoped
    return query.filter_by(company_id=company_id)


def enforce_company_access(obj):
    """
    Raises an exception if the object does not belong to the current user's company.
    """
    if hasattr(current_user, 'company_id') and hasattr(obj, 'company_id'):
        if obj.company_id != current_user.company_id:
            raise PermissionError("Access denied: object does not belong to your company.")
    else:
        raise Exception("Missing company_id attribute on user or object.") 