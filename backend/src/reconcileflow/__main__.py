from __future__ import annotations

import uvicorn

from reconcileflow.settings import Settings


def main() -> None:
    settings = Settings()
    uvicorn.run(
        "reconcileflow.api.app:app",
        host=settings.api_host,
        port=8000,
        reload=False,
    )


if __name__ == "__main__":
    main()
