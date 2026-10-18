from .laboratory_syntheses_models import LaboratorySynthesis, LaboratorySynthesisStatus


LABORATORY_SYNTHESES: list[LaboratorySynthesis] = [
    LaboratorySynthesis(
        laboratory_synthesis_id=1,
        laboratory_synthesis_name='Получение диэтилового эфира',
        laboratory_synthesis_description=(
            "Лабораторный синтез диэтилового эфира из этанола. Карточка объединяет "
            "длительность процесса и температуру, при которой рассматривается получение "
            "продукта. После выделения эфира фактическую массу сравнивают с теоретически "
            "возможной: потери при отделении и очистке влияют на итоговый выход. Масса "
            "исходного реагента и количество полученного вещества вводятся отдельно в "
            "заявке, поэтому их не следует подменять длительностью или температурой "
            "синтеза."
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
            "Лабораторный синтез йодоформа из ацетона с получением жёлтого "
            "кристаллического продукта. Важны не только появление осадка, но и "
            "количество вещества после его выделения и очистки. Часть продукта может "
            "оставаться в смеси или теряться при переносе, поэтому практический выход "
            "обычно отличается от теоретического. В карточке приведены длительность и "
            "температура процесса; для расчёта выхода в заявке используют массы "
            "исходного реагента и выделенного йодоформа."
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
            "Лабораторный синтез ацетилена из карбида кальция; на фотографии показан "
            "исходный реагент. Продукт этой реакции является газом, поэтому сравнение "
            "полученного количества с теоретическим требует единой единицы измерения. "
            "Если результат измерен как объём газа, его приводят к количеству вещества "
            "или массе с учётом условий измерения. Температура и длительность описывают "
            "синтез, а исходные данные для вычисления практического выхода заполняются в "
            "отдельной заявке."
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
            "Получение хлороформа на основе галоформной реакции. Карточка описывает "
            "лабораторный синтез, для которого отдельно учитывают условия проведения и "
            "количество выделенного продукта. При оценке результата важно различать "
            "наличие продукта в реакционной смеси и массу очищенного вещества: они не "
            "равнозначны. Практический выход рассчитывают относительно теоретически "
            "возможного количества по исходному реагенту, а потери при выделении "
            "отражаются в конечном значении процента выхода."
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
