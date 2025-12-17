from constants.expectations.base_expectations import BaseSelectTN3Expected


class Select25Expected(BaseSelectTN3Expected):
    # ----- Base -----
    TEST_SUITE_NAME_VAL = "Select_25_tn3_6km_56"
    TEST_DATA_ARCH_NAME_VAL = "Select25.tar.gz"
    # ----- LeaksInfoExpected -----
    LEAK_COORDINATE_METERS: float = 5400.0
    VOLUME_M3: float = 57
    ALLOWED_TIME_DIFF_SECONDS: int = 1440  # Погрешность времени обнаружения
    ALLOWED_VOLUME_M3 = VOLUME_M3 * BaseSelectTN3Expected.ALLOWED_VOLUME_DIFF  # Абсолютная погрешность по объему
    # ----- LdsStatusExpected -----
    # TODO Изменить значения в рамках задачи LDS-7468
    LEAK_DIAGNOSTIC_AREA_ID_VAL: int = 3
    IN_NEIGHBOR_DIAGNOSTIC_AREA_ID_VAL: int = 2
    OUT_NEIGHBOR_1_DIAGNOSTIC_AREA_ID_VAL: int = 4
    OUT_NEIGHBOR_2_DIAGNOSTIC_AREA_ID_VAL: int = 6
    # ----- OutPutInfoExpected -----
    LEAK_LINEAR_PART_ID_VAL: int = 407
    OUTPUT_ALLOWED_TIME_DIFF_SECONDS: int = ALLOWED_TIME_DIFF_SECONDS + BaseSelectTN3Expected.OUTPUT_TEST_DELAY
