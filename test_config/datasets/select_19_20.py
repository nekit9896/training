"""
Конфигурация тестового набора Select_19_20_tn3_75_181km_649 (две утечки)

Особенности набора:
- Две утечки с разными координатами и временными интервалами
- Первая утечка: 75 км, 648.8 м³, интервал 2460 с (~41 мин)
- Вторая утечка: 181 км, 648.8 м³, интервал 3300 с (~55 мин)
- Интенсивность утечки 20,4%
- Допустимое время обнаружения 6 минут
"""

from constants.enums import TU, ConfirmationStatus, LdsStatus, ReservedType, StationaryStatus
import test_config.models as models

# ===== Константы набора =====
SUITE_NAME = "Select_19_20_tn3_75_181km_649"
SUITE_DATA_ID = 66
ARCHIVE_NAME = f"{SUITE_NAME}.tar.gz"

# Технологический участок
TECHNOLOGICAL_UNIT = TU.TIKHORETSK_NOVOROSSIYSK_3

# ===== Первая утечка =====
LEAK_1_DIAGNOSTIC_AREA_NAME = "Т-Н-3.НПС-5 «Тихорецкая».УЗР вых - Т-Н-3.НПС-3 «Нововеличковская».УЗР вых"
LEAK_1_DIAGNOSTIC_AREA_ID = 2
LEAK_1_CONTROL_SITE_ID = 6032
LEAK_1_LINEAR_PART_ID = 407
LEAK_1_COORDINATE_METERS = 75000.0
LEAK_1_VOLUME_M3 = 648.8
LEAK_1_ALLOWED_TIME_DIFF_SECONDS = 360  # 6 минут
LEAK_1_START_INTERVAL_SECONDS = 2460  # ~41 минута
LEAK_1_OUTPUT_DELAY_SECONDS = 960

# ===== Вторая утечка =====
LEAK_2_DIAGNOSTIC_AREA_NAME = "Т-Н-3.НПС-3 «Нововеличковская».УЗР вых - Т-Н-3.НПС-2 «Крымская».УЗР вх"
LEAK_2_DIAGNOSTIC_AREA_ID = 3
LEAK_2_CONTROL_SITE_ID = 6148
LEAK_2_LINEAR_PART_ID = 408
LEAK_2_COORDINATE_METERS = 181000.0
LEAK_2_VOLUME_M3 = 648.8
LEAK_2_ALLOWED_TIME_DIFF_SECONDS = 360  # 6 минут
LEAK_2_START_INTERVAL_SECONDS = 3300  # ~55 минут
LEAK_2_OUTPUT_DELAY_SECONDS = 150

# ID диагностических участков для проверки статусов
IN_NEIGHBOR_DIAGNOSTIC_AREA_ID = 1
OUT_NEIGHBOR_DIAGNOSTIC_AREA_ID = 3


# ===== Конфигурация набора =====
SELECT_19_20_CONFIG = models.SuiteConfig(
    # ----- Метаданные -----
    suite_name=SUITE_NAME,
    suite_data_id=SUITE_DATA_ID,
    archive_name=ARCHIVE_NAME,
    technological_unit=TECHNOLOGICAL_UNIT,
    
    # ----- Ожидаемый статус стационара -----
    expected_stationary_status=StationaryStatus.STATIONARY.value,
    
    # ===== БАЗОВЫЕ ТЕСТЫ =====
    
    basic_info_test=models.CaseMarkers(
        test_case_id="1",
        offset=1,
        title="[BasicInfo] Проверка базовой информации СОУ: список ТУ",
        tag="BasicInfo",
    ),
    
    journal_info_test=models.CaseMarkers(
        test_case_id="2",
        offset=5,
        title="[MessagesInfo] Проверка наличия сообщений в журнале",
        tag="MessagesInfo",
        description=(
            "Проверка сообщения MessagesInfo.\n"
            "Синхронный запрос для проверки наличия сообщений в поле 'messageInfo'"
        ),
    ),
    
    lds_status_initialization_test=models.CaseMarkers(
        test_case_id="29",
        offset=5,
        title=f"[CommonScheme] Проверка режима работы СОУ: 'Инициализация' на данных {SUITE_NAME}",
        tag="CommonScheme",
        description=(
            f"Проверка режима работы СОУ в сообщении типа: CommonScheme "
            f"на наборе данных {SUITE_NAME}, \n"
            f"на технологическом участке {TECHNOLOGICAL_UNIT.description}\n"
            "Время проведения проверки : ~05:00\n"
            "Ожидаемый режим работы СОУ : Инициализация\n"
        ),
    ),
    
    main_page_info_test=models.CaseMarkers(
        test_case_id="3",
        offset=7,
        title=f"[MainPageInfo] Проверка установки стационара на данных {SUITE_NAME}",
        tag="MainPageInfo",
        description=(
            f"Проверка сообщения MainPageInfo "
            f"об установке режима Стационар на наборе данных {SUITE_NAME}, \n"
            f"на технологическом участке {TECHNOLOGICAL_UNIT.description}\n"
            "Ожидаемое время установки режима Стационар : ~07:00\n"
        ),
    ),
    
    # ----- Дополнительный тест на нестационар (специфика двух утечек) -----
    main_page_info_unstationary_test=models.CaseMarkers(
        test_case_id="79",
        offset=40,
        title=f"[MainPageInfo] Проверка установки не стационара на данных {SUITE_NAME}",
        tag="MainPageInfo",
        description=(
            f"Проверка сообщения MainPageInfo "
            f"об установке режима Не стационар на наборе данных {SUITE_NAME}, \n"
            f"на технологическом участке {TECHNOLOGICAL_UNIT.description}\n"
            "Ожидаемое время установки режима не стационар : ~40:00\n"
        ),
    ),
    
    mask_signal_test=models.CaseMarkers(
        test_case_id="32",
        offset=8.0,
        title=f"[MaskSignal] проверка маскирования датчиков на данных {SUITE_NAME}",
        tag="MaskSignal",
        description=(
            "Проверка работы маскирования и снятия маскирования через синхронные запросы типа: "
            f"MaskSignalRequest и UnmaskSignalRequest, на наборе данных {SUITE_NAME}, \n"
            f"на технологическом участке {TECHNOLOGICAL_UNIT.description}\n"
            "Проверки:\n"
            "Статус-код ответа на синхронный запрос MaskSignalRequest.\n"
            "Значение в поле isMasked сигнала в запросе InputSignalsContent после маскирования.\n"
            "Статус-код ответа на синхронный запрос UnmaskSignalRequest.\n"
            "Значение в поле isMasked сигнала в запросе InputSignalsContent после маскирования.\n"
            "Примечание: что бы не повлиять на проверки утечек, тест на маскирование выполняется во время инициализации."
        ),
    ),
    
    lds_status_initialization_out_test=models.CaseMarkers(
        test_case_id="30",
        offset=30,
        title=f"[CommonScheme] Проверка выхода СОУ из Инициализации на данных {SUITE_NAME}",
        tag="CommonScheme",
        description=(
            f"Проверка режима работы СОУ в сообщении типа: CommonScheme "
            f"на наборе данных {SUITE_NAME}, \n"
            f"на технологическом участке {TECHNOLOGICAL_UNIT.description}\n"
            "Время проведения проверки : ~30:00\n"
            "Ожидаемый результат : режим работы СОУ не 'Инициализация'\n"
        ),
    ),
    
    lds_status_during_leak_test=models.CaseMarkers(
        test_case_id="80",
        offset=47.0,
        title=f"[CommonScheme] Проверка режима работы СОУ во время утечки на данных {SUITE_NAME}",
        tag="CommonScheme",
        description=(
            f"Проверка режима работы СОУ во время утечки в сообщении типа: CommonScheme "
            f"на наборе данных {SUITE_NAME}, \n"
            f"на технологическом участке {TECHNOLOGICAL_UNIT.description}\n"
            "Время проведения проверки : 47:00\n"
            "Примечание: проверка режимов СОУ во время утечки должна выполняться раньше теста на квитирование\n"
            "В рамках данного теста проверяется режим СОУ на ДУ с утечкой и на соседних ДУ"
        ),
    ),
    
    # ===== КОНФИГУРАЦИЯ СТАТУСОВ СОУ ВО ВРЕМЯ УТЕЧКИ =====
    lds_status_during_leak_config=models.DiagnosticAreaStatusConfig(
        diagnostic_area_id=LEAK_1_DIAGNOSTIC_AREA_ID,
        expected_lds_status=LdsStatus.INITIALIZATION.value,
        in_neighbor_id=IN_NEIGHBOR_DIAGNOSTIC_AREA_ID,
        in_neighbor_status=LdsStatus.DEGRADATION.value,
        out_neighbor_id=OUT_NEIGHBOR_DIAGNOSTIC_AREA_ID,
        out_neighbor_status=LdsStatus.DEGRADATION.value,
    ),
    
    # ===== Конфигурации утечек =====
    leaks=[
        # ===== ПЕРВАЯ УТЕЧКА (75 км) =====
        models.LeakTestConfig(
            # ----- Идентификаторы -----
            diagnostic_area_name=LEAK_1_DIAGNOSTIC_AREA_NAME,
            diagnostic_area_id=LEAK_1_DIAGNOSTIC_AREA_ID,
            control_site_id=LEAK_1_CONTROL_SITE_ID,
            linear_part_id=LEAK_1_LINEAR_PART_ID,
            
            # ----- Параметры утечки -----
            coordinate_meters=LEAK_1_COORDINATE_METERS,
            volume_m3=LEAK_1_VOLUME_M3,
            
            # ----- Временные интервалы -----
            leak_start_interval_seconds=LEAK_1_START_INTERVAL_SECONDS,
            allowed_time_diff_seconds=LEAK_1_ALLOWED_TIME_DIFF_SECONDS,
            output_test_delay_seconds=LEAK_1_OUTPUT_DELAY_SECONDS,
            
            # ----- Ожидаемые статусы -----
            expected_lds_status=LdsStatus.SERVICEABLE.value,
            expected_stationary_status=StationaryStatus.UNSTATIONARY.value,
            
            # ----- Тест LeaksContent (первая утечка) -----
            leaks_content_test=models.CaseMarkers(
                test_case_id="72",
                offset=47.0,
                title=f"[LeaksContent] проверка первой утечки на данных {SUITE_NAME}",
                tag="LeaksContent",
                description=(
                    f"Проверка сообщения LeaksContent "
                    f"о первой утечке на наборе данных {SUITE_NAME}, \n"
                    f"на технологическом участке {TECHNOLOGICAL_UNIT.description}\n"
                    "Ожидаемое окно возникновения утечки: ~37:00 - 43:00\n"
                    f"Ожидаемое ДУ возникновения утечки: {LEAK_1_DIAGNOSTIC_AREA_NAME}\n"
                    "Допустимое время обнаружения 6 минут с момента начала утечки, "
                    f"т к для данных {SUITE_NAME} интенсивность утечки 20,4%.\n"
                    "Примечание: тесты сообщений об утечке должны выполняться раньше теста на квитирование"
                ),
            ),
            
            # ----- Тест AllLeaksInfo (первая утечка) -----
            all_leaks_info_test=models.CaseMarkers(
                test_case_id="66",
                offset=47.0,
                title=f"[AllLeaksInfo] проверка первой утечки на данных {SUITE_NAME}",
                tag="AllLeaksInfo",
                description=(
                    f"Проверка сообщения AllLeaksInfo "
                    f"о первой утечке на наборе данных {SUITE_NAME}, \n"
                    f"на технологическом участке {TECHNOLOGICAL_UNIT.description}\n"
                    "Ожидаемое окно возникновения утечки: ~41:00 - 47:00\n"
                    f"Ожидаемое ДУ возникновения утечки: {LEAK_1_DIAGNOSTIC_AREA_NAME}\n"
                    "Допустимое время обнаружения 6 минут с момента начала утечки, "
                    f"т к для данных {SUITE_NAME} интенсивность утечки 20,4%.\n"
                    "Примечание: тесты сообщений об утечке должны выполняться раньше теста на квитирование"
                ),
            ),
            
            # ----- Тест TuLeaksInfo (первая утечка) -----
            tu_leaks_info_test=models.CaseMarkers(
                test_case_id="70",
                offset=47.0,
                title=f"[TuLeaksInfo] проверка первой утечки на данных {SUITE_NAME}",
                tag="TuLeaksInfo",
                description=(
                    f"Проверка сообщения TuLeaksInfo "
                    f"о первой утечке на наборе данных {SUITE_NAME}, \n"
                    f"на технологическом участке {TECHNOLOGICAL_UNIT.description}\n"
                    "Ожидаемое окно возникновения утечки: ~41:00 - 47:00\n"
                    "Допустимое время обнаружения 6 минут с момента начала утечки, "
                    f"т к для данных {SUITE_NAME} интенсивность утечки 20,4%.\n"
                    "Примечание: тесты сообщений об утечке должны выполняться раньше теста на квитирование"
                ),
            ),
            
            # ----- Тест AcknowledgeLeak (первая утечка) -----
            acknowledge_leak_test=models.CaseMarkers(
                test_case_id="74",
                offset=62.0,
                title=f"[AcknowledgeLeak] проверка квитирования первой утечки на данных {SUITE_NAME}",
                tag="AcknowledgeLeak",
                description=(
                    "Проверка квитирования первой утечки через синхронный запрос типа: AcknowledgeLeakRequest "
                    f"на наборе данных {TECHNOLOGICAL_UNIT.description}, \n"
                    f"на технологическом участке {TECHNOLOGICAL_UNIT.description}\n"
                    f"Ожидаемое ДУ возникновения утечки: {LEAK_1_DIAGNOSTIC_AREA_NAME}\n"
                    "Проверки:\n"
                    "Статус-код ответа на синхронный запрос AcknowledgeLeakRequest,\n"
                    "Отсутствие сообщений об утечках в AllLeaksInfoContent после квитирования"
                ),
            ),
            
            # ----- Тест OutputSignals (первая утечка) -----
            output_signals_test=models.CaseMarkers(
                test_case_id="77",
                offset=63.0,
                title=f"[OutputSignalsInfo] Проверка данных о первой утечке в выходных сигналах на линейном участке с id: {LEAK_1_LINEAR_PART_ID}",
                tag="OutputSignals",
                description=(
                    "Проверка наличия данных о первой утечке в выходных сигналах "
                    f"на наборе данных {SUITE_NAME}, \n"
                    f"на технологическом участке {TECHNOLOGICAL_UNIT.description}\n"
                    "Получение списка выходных сигналов для линейного участка, запросом: GetOutputSignalsRequest\n"
                    "Получение данных выходных сигналов для линейного участка, по подписке: SubscribeOutputSignalsRequest\n"
                    "Примечание: "
                    "Данный тест так же проверяет квитирование, время запуска выставлять после запуска теста на квитирование утечки"
                ),
            ),
        ),
        
        # ===== ВТОРАЯ УТЕЧКА (181 км) =====
        models.LeakTestConfig(
            # ----- Идентификаторы -----
            diagnostic_area_name=LEAK_2_DIAGNOSTIC_AREA_NAME,
            diagnostic_area_id=LEAK_2_DIAGNOSTIC_AREA_ID,
            control_site_id=LEAK_2_CONTROL_SITE_ID,
            linear_part_id=LEAK_2_LINEAR_PART_ID,
            
            # ----- Параметры утечки -----
            coordinate_meters=LEAK_2_COORDINATE_METERS,
            volume_m3=LEAK_2_VOLUME_M3,
            
            # ----- Временные интервалы -----
            leak_start_interval_seconds=LEAK_2_START_INTERVAL_SECONDS,
            allowed_time_diff_seconds=LEAK_2_ALLOWED_TIME_DIFF_SECONDS,
            output_test_delay_seconds=LEAK_2_OUTPUT_DELAY_SECONDS,
            
            # ----- Ожидаемые статусы -----
            expected_lds_status=LdsStatus.DEGRADATION.value,
            expected_stationary_status=StationaryStatus.UNSTATIONARY.value,
            
            # ----- Тест LeaksContent (вторая утечка) -----
            leaks_content_test=models.CaseMarkers(
                test_case_id="73",
                offset=61.0,
                title=f"[LeaksContent] проверка второй утечки на данных {SUITE_NAME}",
                tag="LeaksContent",
                description=(
                    f"Проверка сообщения LeaksContent "
                    f"о второй утечке на наборе данных {SUITE_NAME}, \n"
                    f"на технологическом участке {TECHNOLOGICAL_UNIT.description}\n"
                    "Ожидаемое окно возникновения утечки: ~55:00 - 61:00\n"
                    f"Ожидаемое ДУ возникновения утечки: {LEAK_2_DIAGNOSTIC_AREA_NAME}\n"
                    "Допустимое время обнаружения 6 минут с момента начала утечки, "
                    f"т к для данных {SUITE_NAME} интенсивность утечки 20,4%.\n"
                    "Примечание: тесты сообщений об утечке должны выполняться раньше теста на квитирование"
                ),
            ),
            
            # ----- Тест AllLeaksInfo (вторая утечка) -----
            all_leaks_info_test=models.CaseMarkers(
                test_case_id="69",
                offset=61.0,
                title=f"[AllLeaksInfo] проверка второй утечки на данных {SUITE_NAME}",
                tag="AllLeaksInfo",
                description=(
                    f"Проверка сообщения AllLeaksInfo "
                    f"о второй утечке на наборе данных {SUITE_NAME}, \n"
                    f"на технологическом участке {TECHNOLOGICAL_UNIT.description}\n"
                    "Ожидаемое окно возникновения утечки: ~55:00 - 61:00\n"
                    f"Ожидаемое ДУ возникновения утечки: {LEAK_2_DIAGNOSTIC_AREA_NAME}\n"
                    "Допустимое время обнаружения 6 минут с момента начала утечки, "
                    f"т к для данных {SUITE_NAME} интенсивность утечки 20,4%.\n"
                    "Примечание: тесты сообщений об утечке должны выполняться раньше теста на квитирование"
                ),
            ),
            
            # ----- Тест TuLeaksInfo (вторая утечка) -----
            tu_leaks_info_test=models.CaseMarkers(
                test_case_id="71",
                offset=61.0,
                title=f"[TuLeaksInfo] проверка второй утечки на данных {SUITE_NAME}",
                tag="TuLeaksInfo",
                description=(
                    f"Проверка сообщения TuLeaksInfo "
                    f"о второй утечке на наборе данных {SUITE_NAME}, \n"
                    f"на технологическом участке {TECHNOLOGICAL_UNIT.description}\n"
                    "Ожидаемое окно возникновения утечки: ~55:00 - 61:00\n"
                    "Допустимое время обнаружения 6 минут с момента начала утечки, "
                    f"т к для данных {SUITE_NAME} интенсивность утечки 20,4%.\n"
                    "Примечание: тесты сообщений об утечке должны выполняться раньше теста на квитирование"
                ),
            ),
            
            # ----- Тест AcknowledgeLeak (вторая утечка) -----
            acknowledge_leak_test=models.CaseMarkers(
                test_case_id="75",
                offset=62.5,
                title=f"[AcknowledgeLeak] проверка квитирования второй утечки на данных {SUITE_NAME}",
                tag="AcknowledgeLeak",
                description=(
                    "Проверка квитирования второй утечки через синхронный запрос типа: AcknowledgeLeakRequest "
                    f"на наборе данных {SUITE_NAME}, \n"
                    f"на технологическом участке {TECHNOLOGICAL_UNIT.description}\n"
                    f"Ожидаемое ДУ возникновения утечки: {LEAK_2_DIAGNOSTIC_AREA_NAME}\n"
                    "Проверки:\n"
                    "Статус-код ответа на синхронный запрос AcknowledgeLeakRequest,\n"
                    "Отсутствие сообщений об утечках в AllLeaksInfoContent после квитирования"
                ),
            ),
            
            # ----- Тест OutputSignals (вторая утечка) -----
            output_signals_test=models.CaseMarkers(
                test_case_id="78",
                offset=63.5,
                title=f"[OutputSignalsInfo] Проверка данных о второй утечке в выходных сигналах на линейном участке с id: {LEAK_2_LINEAR_PART_ID}",
                tag="OutputSignals",
                description=(
                    "Проверка наличия данных о второй утечке в выходных сигналах "
                    f"на наборе данных {SUITE_NAME}, \n"
                    f"на технологическом участке {TECHNOLOGICAL_UNIT.description}\n"
                    "Получение списка выходных сигналов для линейного участка, запросом: GetOutputSignalsRequest\n"
                    "Получение данных выходных сигналов для линейного участка, по подписке: SubscribeOutputSignalsRequest\n"
                    "Примечание: "
                    "Данный тест так же проверяет квитирование, время запуска выставлять после запуска теста на квитирование утечки"
                ),
            ),
        ),
    ],
)


# Экспортируем дополнительные константы для специфичных проверок
class Select19Constants:
    """Дополнительные константы для select_19_20"""
    
    CONFIRMATION_STATUS = ConfirmationStatus
    RESERVED_TYPE = ReservedType
