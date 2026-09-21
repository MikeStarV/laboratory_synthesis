from .laboratory_syntheses_models import (
    LaboratorySynthesis,
    LaboratorySynthesisStatus,
)


LABORATORY_SYNTHESES: list[LaboratorySynthesis] = [
    LaboratorySynthesis(
        laboratory_synthesis_id=1,
        laboratory_synthesis_name="Получение диэтилового эфира",
        laboratory_synthesis_description=(
            "Лабораторный синтез диэтилового эфира из этанола. "
            "Полученный продукт выделяют и определяют его массу. "
            "Эти данные вместе с массой исходного реагента используются "
            "в заявке для расчёта практического выхода относительно "
            "теоретически возможного."
        ),
        laboratory_synthesis_duration_minutes=90,
        laboratory_synthesis_temperature_celsius=135,
        laboratory_synthesis_image_key="ether_synthesis.jpg",
        laboratory_synthesis_video_key="ether_synthesis.mp4",
        laboratory_synthesis_status=(
            LaboratorySynthesisStatus.PUBLISHED
        ),
        laboratory_synthesis_liked_by_user_ids=[
            101,
            102,
            103,
            104,
        ],
    ),
    LaboratorySynthesis(
        laboratory_synthesis_id=2,
        laboratory_synthesis_name="Получение йодоформа",
        laboratory_synthesis_description=(
            "Лабораторный синтез йодоформа из ацетона. "
            "Продукт представляет собой жёлтое кристаллическое вещество. "
            "Масса выделенного продукта и масса исходного реагента служат "
            "исходными данными для расчёта выхода в заявке."
        ),
        laboratory_synthesis_duration_minutes=45,
        laboratory_synthesis_temperature_celsius=50,
        laboratory_synthesis_image_key="iodoform_synthesis.jpg",
        laboratory_synthesis_video_key="iodoform_synthesis.mp4",
        laboratory_synthesis_status=(
            LaboratorySynthesisStatus.PUBLISHED
        ),
        laboratory_synthesis_liked_by_user_ids=[
            101,
            105,
        ],
    ),
    LaboratorySynthesis(
        laboratory_synthesis_id=3,
        laboratory_synthesis_name="Получение ацетилена",
        laboratory_synthesis_description=(
            "Лабораторный синтез ацетилена из карбида кальция. "
            "Для расчёта выхода количество полученного газа приводят "
            "к массе с учётом условий измерения. В заявке сравнивают "
            "фактическую массу продукта с теоретической."
        ),
        laboratory_synthesis_duration_minutes=20,
        laboratory_synthesis_temperature_celsius=20,
        laboratory_synthesis_image_key="acetylene_synthesis.jpg",
        laboratory_synthesis_video_key="acetylene_synthesis.mp4",
        laboratory_synthesis_status=(
            LaboratorySynthesisStatus.PUBLISHED
        ),
        laboratory_synthesis_liked_by_user_ids=[],
    ),
    LaboratorySynthesis(
        laboratory_synthesis_id=4,
        laboratory_synthesis_name="Получение хлороформа",
        laboratory_synthesis_description=(
            "Лабораторный синтез хлороформа на основе галоформной реакции. "
            "Выделенный продукт характеризуют и взвешивают. "
            "Результат измерения нужен для последующего расчёта "
            "практического выхода продукта."
        ),
        laboratory_synthesis_duration_minutes=60,
        laboratory_synthesis_temperature_celsius=60,
        laboratory_synthesis_image_key="chloroform_synthesis.jpg",
        laboratory_synthesis_video_key="chloroform_synthesis.mp4",
        laboratory_synthesis_status=(
            LaboratorySynthesisStatus.PUBLISHED
        ),
        laboratory_synthesis_liked_by_user_ids=[102],
    ),
    LaboratorySynthesis(
        laboratory_synthesis_id=5,
        laboratory_synthesis_name="Получение бромэтана",
        laboratory_synthesis_description=(
            "Лабораторный синтез бромэтана из этанола. "
            "Эта запись удалена и не отображается посетителям."
        ),
        laboratory_synthesis_duration_minutes=75,
        laboratory_synthesis_temperature_celsius=80,
        laboratory_synthesis_image_key=(
            "laboratory_syntheses_bromoethane.svg"
        ),
        laboratory_synthesis_video_key=(
            "laboratory_syntheses_bromoethane.mp4"
        ),
        laboratory_synthesis_status=(
            LaboratorySynthesisStatus.DELETED
        ),
        laboratory_synthesis_liked_by_user_ids=[],
    ),
    LaboratorySynthesis(
        laboratory_synthesis_id=6,
        laboratory_synthesis_name="Получение этилена",
        laboratory_synthesis_description=(
            "Лабораторный синтез этилена из этанола. "
            "Количество полученного продукта используется для расчёта "
            "выхода относительно теоретически возможного."
        ),
        laboratory_synthesis_duration_minutes=40,
        laboratory_synthesis_temperature_celsius=170,
        laboratory_synthesis_image_key=(
            "laboratory_syntheses_ethylene.svg"
        ),
        laboratory_synthesis_video_key=(
            "laboratory_syntheses_ethylene.mp4"
        ),
        laboratory_synthesis_status=(
            LaboratorySynthesisStatus.DRAFT
        ),
        laboratory_synthesis_liked_by_user_ids=[],
    ),
]
