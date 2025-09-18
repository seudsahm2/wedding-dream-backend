from typing import Any, Dict
from rest_framework.views import exception_handler as drf_exception_handler
from rest_framework.response import Response


def exception_handler(exc: Exception, context: Dict[str, Any]) -> Response | None:
    response = drf_exception_handler(exc, context)
    if response is None:
        return response

    # Normalize payload: always include top-level detail and errors (if applicable)
    data = response.data
    if isinstance(data, dict):
        detail = data.get("detail")
        if detail is None:
            # Construct a summary from first error field if possible
            if data:
                first_key = next(iter(data.keys()))
                first_val = data[first_key]
                if isinstance(first_val, list) and first_val:
                    detail = str(first_val[0])
                else:
                    detail = str(first_val)
            else:
                detail = response.status_text
        normalized = {"detail": detail}
        # Keep field errors under "errors"
        field_errors = {k: v for k, v in data.items() if k != "detail"}
        if field_errors:
            normalized["errors"] = field_errors
        response.data = normalized
    return response
