from typing import Annotated
from pydantic import BeforeValidator
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .laboratory_syntheses_data import LABORATORY_SYNTHESES
from .laboratory_syntheses_models import LaboratorySynthesisStatus
from .laboratory_syntheses_media import LABORATORY_SYNTHESES_DIRECTORY, laboratory_synthesis_media_url

app = FastAPI(title="Лабораторные синтезы — расчёт выхода продукта", docs_url=None, redoc_url=None, openapi_url=None)
app.mount("/laboratory_syntheses/static", StaticFiles(directory=LABORATORY_SYNTHESES_DIRECTORY / "static"), name="laboratory_syntheses_static")
laboratory_syntheses_templates = Jinja2Templates(directory=LABORATORY_SYNTHESES_DIRECTORY / "templates")
laboratory_syntheses_templates.env.globals["laboratory_synthesis_media_url"] = laboratory_synthesis_media_url


def published_laboratory_syntheses():
    return sorted(
        (laboratory_synthesis for laboratory_synthesis in LABORATORY_SYNTHESES
         if laboratory_synthesis.laboratory_synthesis_status == LaboratorySynthesisStatus.PUBLISHED),
        key=lambda laboratory_synthesis: laboratory_synthesis.laboratory_synthesis_id,
    )


@app.get("/", include_in_schema=False)
def laboratory_syntheses_home():
    return RedirectResponse("/laboratory_syntheses", status_code=307)


@app.get("/laboratory_syntheses")
def laboratory_syntheses_catalog(
    request: Request,
    laboratory_synthesis_max_duration: Annotated[int | None, Query(ge=0, le=240), BeforeValidator(lambda value: None if value == "" else value)] = None,
):
    laboratory_syntheses = published_laboratory_syntheses()
    if laboratory_synthesis_max_duration is not None:
        laboratory_syntheses = [laboratory_synthesis for laboratory_synthesis in laboratory_syntheses
                               if laboratory_synthesis.laboratory_synthesis_duration_minutes <= laboratory_synthesis_max_duration]
    return laboratory_syntheses_templates.TemplateResponse(request=request, name="laboratory_syntheses_catalog.html", context={
        "laboratory_syntheses_active_page": "catalog",
        "laboratory_syntheses": laboratory_syntheses,
        "laboratory_syntheses_likes": {laboratory_synthesis.laboratory_synthesis_id: len(laboratory_synthesis.laboratory_synthesis_liked_by_user_ids) for laboratory_synthesis in laboratory_syntheses},
        "laboratory_synthesis_max_duration": laboratory_synthesis_max_duration,
    })


@app.get("/laboratory_syntheses/draft")
def laboratory_syntheses_draft(request: Request):
    laboratory_synthesis = next((laboratory_synthesis for laboratory_synthesis in LABORATORY_SYNTHESES
                                if laboratory_synthesis.laboratory_synthesis_status == LaboratorySynthesisStatus.DRAFT), None)
    if laboratory_synthesis is None:
        raise HTTPException(404, "Черновик лабораторного синтеза отсутствует")
    return laboratory_syntheses_templates.TemplateResponse(request=request, name="laboratory_syntheses_draft.html", context={
        "laboratory_syntheses_active_page": "draft", "laboratory_synthesis": laboratory_synthesis,
    })


@app.get("/laboratory_syntheses/feed")
@app.get("/laboratory_syntheses/feed/{laboratory_synthesis_id}")
def laboratory_syntheses_feed(
    request: Request,
    laboratory_synthesis_id: int | None = None,
    laboratory_synthesis_next: Annotated[bool, Query(alias="next")] = False,
):
    laboratory_syntheses = published_laboratory_syntheses()
    if not laboratory_syntheses:
        raise HTTPException(404, "Нет опубликованных лабораторных синтезов")
    laboratory_synthesis_index = 0
    if laboratory_synthesis_id is not None:
        laboratory_synthesis_index = next((index for index, laboratory_synthesis in enumerate(laboratory_syntheses)
                                          if laboratory_synthesis.laboratory_synthesis_id == laboratory_synthesis_id), -1)
        if laboratory_synthesis_index == -1:
            raise HTTPException(404, "Лабораторный синтез не найден")
        if laboratory_synthesis_next:
            laboratory_synthesis_index = (laboratory_synthesis_index + 1) % len(laboratory_syntheses)
    laboratory_synthesis = laboratory_syntheses[laboratory_synthesis_index]
    return laboratory_syntheses_templates.TemplateResponse(request=request, name="laboratory_syntheses_feed.html", context={
        "laboratory_syntheses_active_page": "feed", "laboratory_synthesis": laboratory_synthesis,
        "laboratory_synthesis_likes": len(laboratory_synthesis.laboratory_synthesis_liked_by_user_ids),
        "laboratory_synthesis_position": laboratory_synthesis_index + 1,
        "laboratory_syntheses_count": len(laboratory_syntheses),
    })
