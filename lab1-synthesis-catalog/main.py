from fastapi import FastAPI, Request, Query, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse

from data import SYNTHESIS_CATALOG
from models import SynthesisStatus
from minio_client import build_media_url

app = FastAPI(title="Synthesis Yield Catalog - Lab 1")

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


def get_published_synthesis_list():
    return [s for s in SYNTHESIS_CATALOG if s.status == SynthesisStatus.PUBLISHED]


def find_synthesis_by_id(synthesis_id: int):
    return next((s for s in SYNTHESIS_CATALOG if s.id == synthesis_id), None)


def find_next_published_id(current_id: int):
    published = sorted(get_published_synthesis_list(), key=lambda s: s.id)
    ids = [s.id for s in published]
    if current_id not in ids:
        return ids[0] if ids else None
    idx = ids.index(current_id)
    return ids[idx + 1] if idx + 1 < len(ids) else ids[0]


def get_yield_badge_color(percent: float) -> str:
    """Возвращает hex-цвет бейджа в зависимости от эталонного % выхода."""
    if percent >= 70:
        return "#4AD66D"   # зелёный
    if percent >= 50:
        return "#E9C46A"   # жёлтый
    return "#E76F51"       # оранжевый


@app.get("/")
def root():
    first = get_published_synthesis_list()[0]
    return RedirectResponse(url=f"/synthesis-feed/{first.id}")


@app.get("/synthesis-feed/{synthesis_id}")
def synthesis_feed(request: Request, synthesis_id: int, next: bool = Query(default=False)):
    target_id = synthesis_id
    if next:
        next_id = find_next_published_id(synthesis_id)
        if next_id is None:
            raise HTTPException(status_code=404, detail="Нет доступных синтезов")
        target_id = next_id

    synthesis = find_synthesis_by_id(target_id)
    if synthesis is None or synthesis.status != SynthesisStatus.PUBLISHED:
        raise HTTPException(status_code=404, detail="Синтез не найден или не опубликован")

    return templates.TemplateResponse(
        "feed.html",
        {
            "request": request,
            "active_page": "feed",
            "synthesis": synthesis,
            "image_url": build_media_url(synthesis.imageKey),
            "video_url": build_media_url(synthesis.videoKey),
            "likes_count": len(synthesis.likedByUserIds),
            "next_id": find_next_published_id(target_id),
        },
    )


@app.get("/synthesis-draft")
def synthesis_draft(request: Request):
    draft = next((s for s in SYNTHESIS_CATALOG if s.status == SynthesisStatus.DRAFT), None)
    if draft is None:
        raise HTTPException(status_code=404, detail="Черновик отсутствует")

    return templates.TemplateResponse(
        "draft.html",
        {
            "request": request,
            "active_page": "draft",
            "synthesis": draft,
            "image_url": build_media_url(draft.imageKey),
            "video_url": build_media_url(draft.videoKey),
        },
    )


@app.get("/synthesis-catalog")
def synthesis_catalog(request: Request, reagent_mass: float | None = Query(default=None)):
    items = get_published_synthesis_list()
    if reagent_mass is not None:
        items = [s for s in items if s.reagentMass >= reagent_mass]

    cards = [
        {
            "id": s.id,
            "name": s.name,
            "image_url": build_media_url(s.imageKey),
            "likes_count": len(s.likedByUserIds),
            "reagent_name": s.reagentName,
            "reference_yield_percent": s.referenceYieldPercent,
            "badge_color": get_yield_badge_color(s.referenceYieldPercent),
        }
        for s in items
    ]

    return templates.TemplateResponse(
        "catalog.html",
        {
            "request": request,
            "active_page": "catalog",
            "cards": cards,
            "reagent_mass_filter": reagent_mass,
        },
    )
