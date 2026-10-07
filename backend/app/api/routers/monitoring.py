"""Monitoring — metriques serveur, historique, agents (Linux/Windows futur)."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import sys
from pathlib import Path
for _p in (Path(__file__).resolve().parents[2] / "core",
           Path("/opt/infraos/backend/app/core")):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
from infraos import monitoring as mon
from deps import require_role

router = APIRouter()


class AgentBody(BaseModel):
    hostname: str
    os: str = "linux"
    token: str = ""


class PushBody(BaseModel):
    hostname: str
    token: str
    metrics: dict = {}


@router.get("/current")
def current(user: dict = Depends(require_role("operator"))):
    return mon.current()


@router.post("/collect")
def collect(user: dict = Depends(require_role("operator"))):
    return mon.collect()


@router.get("/history")
def history(host: str = "local", limit: int = 60,
            user: dict = Depends(require_role("operator"))):
    return {"host": host, "samples": mon.history(host, limit)}


@router.get("/agents")
def list_agents(user: dict = Depends(require_role("operator"))):
    return {"agents": mon.agents()}


@router.post("/agents")
def register_agent(body: AgentBody, user: dict = Depends(require_role("admin"))):
    try:
        return mon.register_agent(body.hostname, body.os, body.token)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/agents/push")
def agent_push(body: PushBody):
    """Push agent (auth par token agent, pas JWT — protocole docs/AGENT.md)."""
    try:
        return mon.agent_push(body.hostname, body.token, body.metrics)
    except ValueError as e:
        raise HTTPException(401, str(e))
