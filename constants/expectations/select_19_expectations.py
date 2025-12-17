from constants.expectations.base_expectations import BaseSelectTN3Expected


class Select19Expected(BaseSelectTN3Expected):
    # ----- Base -----
    TEST_SUITE_NAME_VAL: str = "Select_19_20_tn3_75_181km_649"
    TEST_DATA_ARCH_NAME_VAL: str = f"{TEST_SUITE_NAME_VAL}.tar.gz"
    # ----- Leak1Expected -----
    LEAK_1_DIAGNOSTIC_AREA_NAME_VAL: str = "Т-Н-3.НПС-5 «Тихорецкая».УЗР вых - Т-Н-3.НПС-3 «Нововеличковская».УЗР вых"
    LEAK_1_DIAGNOSTIC_AREA_ID_VAL: int = 2
    IN_NEIGHBOR_DIAGNOSTIC_AREA_ID_VAL: int = 1
    OUT_NEIGHBOR_DIAGNOSTIC_AREA_ID_VAL: int = 3
    LEAK_1_CONTROL_SITE_ID_VAL: int = 6032
    LEAK_1_LINEAR_PART_ID_VAL: int = 407
    LEAK_1_COORDINATE_METERS: float = 75000.0
    LEAK_1_VOLUME_M3: float = 648.8
    LEAK_1_ALLOWED_TIME_DIFF_SECONDS: int = 360  # Погрешность времени обнаружения утечки
    LEAK_1_ALLOWED_VOLUME_M3: float = LEAK_1_VOLUME_M3 * BaseSelectTN3Expected.ALLOWED_VOLUME_DIFF
    # ----- Leak2Expected -----
    LEAK_2_DIAGNOSTIC_AREA_NAME_VAL: str = "Т-Н-3.НПС-3 «Нововеличковская».УЗР вых - Т-Н-3.НПС-2 «Крымская».УЗР вх"
    LEAK_2_CONTROL_SITE_ID_VAL: int = 6148
    LEAK_2_LINEAR_PART_ID_VAL: int = 408
    LEAK_2_COORDINATE_METERS: float = 181000.0
    LEAK_2_VOLUME_M3: float = 648.8
    LEAK_2_ALLOWED_TIME_DIFF_SECONDS: int = 360  # Погрешность времени обнаружения утечки
    LEAK_2_ALLOWED_VOLUME_M3: float = LEAK_2_VOLUME_M3 * BaseSelectTN3Expected.ALLOWED_VOLUME_DIFF
    # ----- OutPutInfoExpected -----
    LEAK_1_OUTPUT_TEST_DELAY_S: int = 960
    LEAK_2_OUTPUT_TEST_DELAY_S: int = 150
    LEAK_1_OUTPUT_ALLOWED_TIME_DIFF_S: int = LEAK_1_ALLOWED_TIME_DIFF_SECONDS + LEAK_1_OUTPUT_TEST_DELAY_S
    LEAK_2_OUTPUT_ALLOWED_TIME_DIFF_S: int = LEAK_2_ALLOWED_TIME_DIFF_SECONDS + LEAK_2_OUTPUT_TEST_DELAY_S
