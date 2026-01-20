from constants.expectations.base_expectations import BaseSelectTN3Expected


class Select17Expected(BaseSelectTN3Expected):
    # ----- Base -----
    TEST_SUITE_NAME_VAL = "Select_17_tn3_75km_417"
    TEST_DATA_ARCH_NAME_VAL = f"{TEST_SUITE_NAME_VAL}.tar.gz"
    # ----- LeaksInfoExpected -----
    LEAK_COORDINATE_METERS: float = 75000.0
    VOLUME_M3: float = 416
    ALLOWED_TIME_DIFF_SECONDS: int = 1440  # Погрешность времени обнаружения
    ALLOWED_VOLUME_M3 = VOLUME_M3 * BaseSelectTN3Expected.ALLOWED_VOLUME_DIFF  # Абсолютная погрешность по объему
    # ----- LdsStatusExpected -----
    LEAK_DIAGNOSTIC_AREA_ID_VAL: int = 2
    IN_NEIGHBOR_DIAGNOSTIC_AREA_ID_VAL: int = 1
    OUT_NEIGHBOR_DIAGNOSTIC_AREA_ID_VAL: int = 3
    # ----- OutPutInfoExpected -----
    LEAK_LINEAR_PART_ID_VAL: int = 407
    OUTPUT_ALLOWED_TIME_DIFF_SECONDS: int = ALLOWED_TIME_DIFF_SECONDS + BaseSelectTN3Expected.OUTPUT_TEST_DELAY
    