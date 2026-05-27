from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .. import strategies, strategy_doc_io

router = APIRouter(prefix="/api/strategies/{sid}/strategy", tags=["strategy_doc"])


class WriteBody(BaseModel):
    markdown: str


@router.get("")
def read_doc(sid: str):
    if not strategies.get_strategy(sid):
        raise HTTPException(404, "strategy not found")
    return {"markdown": strategy_doc_io.read(sid)}


@router.put("")
def write_doc(sid: str, body: WriteBody):
    if not strategies.get_strategy(sid):
        raise HTTPException(404, "strategy not found")
    strategy_doc_io.write(sid, body.markdown)
    return {"ok": True}
