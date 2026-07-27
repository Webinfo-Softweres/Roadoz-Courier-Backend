"""Mobile fleet API error response helpers."""

from fastapi.responses import JSONResponse


def is_mobile_fleet_path(path: str) -> bool:
    return (
        path == "/api/auth/register"
        or path.startswith("/api/driver/")
        or path.startswith("/api/v1/driver/")
        or path.startswith("/api/v1/auth/driver/")
    )


def mobile_error_response(status_code: int, message: str) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"success": False, "message": message})


def validation_error_message(errors: list) -> str:
    if not errors:
        return "Validation failed"
    err = errors[0]
    loc = ".".join(str(part) for part in err.get("loc", ()) if part != "body")
    msg = err.get("msg", "Validation failed")
    return f"{loc}: {msg}" if loc else msg
