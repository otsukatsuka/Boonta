"""Common FastAPI dependencies."""
from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from src.db.session import get_session

DbSession = Annotated[Session, Depends(get_session)]
