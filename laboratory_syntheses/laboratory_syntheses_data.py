from .laboratory_syntheses_models import LaboratorySynthesis, LaboratorySynthesisStatus


LABORATORY_SYNTHESES: list[LaboratorySynthesis] = [
    LaboratorySynthesis(
        laboratory_synthesis_id=1,
        laboratory_synthesis_name='Получение диэтилового эфира',
        laboratory_synthesis_description=(
            "Синтез диэтилового эфира из этанола. В карточке указаны длительность и "
            "температура процесса. Выделенный продукт очищают, а его фактическую "
            "массу сравнивают с теоретически возможной. Потери при отделении и "
            "очистке уменьшают практический выход. Для расчёта в заявке указывают "
            "массы исходного реагента и полученного эфира."
        ),
        laboratory_synthesis_duration_minutes=90,
        laboratory_synthesis_temperature_celsius=135,
        laboratory_synthesis_image_key='ether_synthesis.jpg',
        laboratory_synthesis_video_key='ether_synthesis.mp4',
        laboratory_synthesis_status=LaboratorySynthesisStatus.PUBLISHED,
        laboratory_synthesis_liked_by_user_ids=[101, 102, 103, 104],
    ),
    LaboratorySynthesis(
        laboratory_synthesis_id=2,
        laboratory_synthesis_name='Получение йодоформа',
        laboratory_synthesis_description=(
            "Синтез йодоформа из ацетона с получением жёлтого кристаллического "
            "продукта. После выделения и очистки осадка его массу сравнивают с "
            "теоретически возможной. Часть вещества остаётся в смеси или теряется при "
            "переносе, поэтому практический выход отличается от расчётного. В заявке "
            "указывают массы исходного реагента и выделенного йодоформа."
        ),
        laboratory_synthesis_duration_minutes=45,
        laboratory_synthesis_temperature_celsius=50,
        laboratory_synthesis_image_key='iodoform_synthesis.jpg',
        laboratory_synthesis_video_key='iodoform_synthesis.mp4',
        laboratory_synthesis_status=LaboratorySynthesisStatus.PUBLISHED,
        laboratory_synthesis_liked_by_user_ids=[101, 105],
    ),
    LaboratorySynthesis(
        laboratory_synthesis_id=3,
        laboratory_synthesis_name='Получение ацетилена',
        laboratory_synthesis_description=(
            "Синтез ацетилена из карбида кальция; на фотографии показан исходный "
            "реагент. Полученный газ учитывают по объёму с поправкой на условия "
            "измерения, затем переводят результат в количество вещества или массу. "
            "Длительность и температура описывают процесс, а исходные данные для "
            "расчёта выхода заполняют в отдельной заявке."
        ),
        laboratory_synthesis_duration_minutes=20,
        laboratory_synthesis_temperature_celsius=20,
        laboratory_synthesis_image_key='acetylene_synthesis.jpg',
        laboratory_synthesis_video_key='acetylene_synthesis.mp4',
        laboratory_synthesis_status=LaboratorySynthesisStatus.PUBLISHED,
        laboratory_synthesis_liked_by_user_ids=[],
    ),
    LaboratorySynthesis(
        laboratory_synthesis_id=4,
        laboratory_synthesis_name='Получение хлороформа',
        laboratory_synthesis_description=(
            "Получение хлороформа на основе галоформной реакции. Для оценки "
            "результата учитывают массу очищенного продукта, а не его наличие в "
            "смеси. Практический выход сравнивают с теоретически возможным "
            "количеством по исходному реагенту. Потери при выделении и очистке "
            "отражаются в конечном проценте выхода. В карточке указаны условия "
            "синтеза."
        ),
        laboratory_synthesis_duration_minutes=60,
        laboratory_synthesis_temperature_celsius=60,
        laboratory_synthesis_image_key='chloroform_synthesis.jpg',
        laboratory_synthesis_video_key='chloroform_synthesis.mp4',
        laboratory_synthesis_status=LaboratorySynthesisStatus.PUBLISHED,
        laboratory_synthesis_liked_by_user_ids=[102],
    ),
    LaboratorySynthesis(
        laboratory_synthesis_id=5,
        laboratory_synthesis_name='Получение бромэтана',
        laboratory_synthesis_description=(
            "Лабораторный синтез бромэтана из этанола. Эта запись удалена и не "
            "отображается посетителям."
        ),
        laboratory_synthesis_duration_minutes=75,
        laboratory_synthesis_temperature_celsius=80,
        laboratory_synthesis_image_key='laboratory_syntheses_bromoethane.svg',
        laboratory_synthesis_video_key='laboratory_syntheses_bromoethane.mp4',
        laboratory_synthesis_status=LaboratorySynthesisStatus.DELETED,
        laboratory_synthesis_liked_by_user_ids=[],
    ),
    LaboratorySynthesis(
        laboratory_synthesis_id=6,
        laboratory_synthesis_name='Получение этилена',
        laboratory_synthesis_description=(
            "Лабораторный синтез этилена из этанола. Количество полученного продукта "
            "используется для расчёта выхода относительно теоретически возможного."
        ),
        laboratory_synthesis_duration_minutes=40,
        laboratory_synthesis_temperature_celsius=170,
        laboratory_synthesis_image_key='laboratory_syntheses_ethylene.svg',
        laboratory_synthesis_video_key='laboratory_syntheses_ethylene.mp4',
        laboratory_synthesis_status=LaboratorySynthesisStatus.DRAFT,
        laboratory_synthesis_liked_by_user_ids=[],
    ),
]
