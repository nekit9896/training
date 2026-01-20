from __future__ import annotations

import traceback
from typing import Any, List, Optional, TypeVar

import allure
from assertpy import assert_that
from pytest import fail

ObjectType = TypeVar("ObjectType")


class SoftAssertions:
    """
    Контекстный менеджер для "мягких" сравнений.
    Внутри теста используется так:
        with SoftAssertions() as soft:
            StepCheck(..., failures=soft).actual(...).expected(...).equal_to()
    По выходу, если были ошибки — они прикрепляются к Allure и поднимается Aggregated AssertionError.
    """

    def __init__(self) -> None:
        self.failures: List[str] = []

    def __enter__(self) -> List[str]:
        return self.failures

    def __exit__(self, exc_type, exc_val, exc_tb) -> Optional[bool]:
        # Если внутри контекста появились внешние исключения (не связанные с проверками) — не подавляем их.
        if exc_type is not None:
            return False

        if not self.failures:
            return False

        # Прикрепляем все собранные failure-traceback'и к Allure, чтобы их было удобно смотреть
        joined = "\n\n".join(self.failures)
        allure.attach(joined, name="soft assertion failures", attachment_type=allure.attachment_type.TEXT)

        # Поднимаем итоговую ошибку, чтобы CI увидел падение теста
        raise AssertionError("Soft assertion failures:\n\n" + joined)


class StepMessageBuilder:
    """
    Составляет разные сообщения для allure.step под конкретный вид assert
    """

    def __init__(self, check_step: str, field_name: str) -> None:
        self.check_step = check_step
        self.field_name = field_name

    def _build_message(self, message_parts) -> str:
        """
        Собирает сообщение из списка с нужным разделителем
        """
        return "\n".join([self.check_step] + message_parts)

    @staticmethod
    def _format_val(val: Any) -> str:
        """
        Вспомогательная функция для аккуратного форматирования значения в сообщении.
        Она пытается использовать repr(), но на случай исключения возвращает str().
        """
        try:
            return str(val)
        except TypeError:
            return repr(val)

    @staticmethod
    def _item_count(val: Any) -> int:
        """
        Считает количество элементов, если возможно
        """
        return len(val) if hasattr(val, "__len__") else 0

    def equal_to(
        self,
        exp_value: Any,
        act_value: Any,
    ) -> str:
        message_parts = [
            f"Ожидаемый результат: {self.field_name} = {self._format_val(exp_value)}",
            f"Фактический результат: {self.field_name} = {self._format_val(act_value)}",
        ]
        return self._build_message(message_parts)

    def is_not_equal_to(
        self,
        exp_value: Any,
        act_value: Any,
    ) -> str:
        message_parts = [
            f"Ожидаемый результат: {self.field_name} = {self._format_val(exp_value)} не равен фактическому",
            f"Фактический результат: {self.field_name} = {self._format_val(act_value)}",
        ]
        return self._build_message(message_parts)

    def is_not_none(self, act_value: Any) -> str:
        message_parts = [
            f"Ожидаемый результат: {self.field_name} не пустой",
            f"Фактический результат: {self.field_name} = {self._format_val(act_value)}",
        ]
        return self._build_message(message_parts)

    def is_not_empty(self, act_value: Any) -> str:
        item_count = self._item_count(act_value)
        message_parts = [
            f"Ожидаемый результат: {self.field_name} содержит хотя бы один элемент",
            f"Фактический результат: количество элементов в {self.field_name} = {item_count}",
        ]
        return self._build_message(message_parts)

    def is_empty(self, act_value: Any) -> str:
        item_count = self._item_count(act_value)
        message_parts = [
            f"Ожидаемый результат: {self.field_name} не содержит элементов",
            f"Фактический результат: количество элементов в {self.field_name} = {item_count}",
        ]
        return self._build_message(message_parts)

    def is_close_to(self, exp_value: Any, act_value: Any, extra_info: Optional[Any] = None) -> str:
        message_parts = [
            f"Ожидаемый результат: {self.field_name} = {self._format_val(exp_value)}",
            f"Фактический результат: {self.field_name} = {self._format_val(act_value)}",
        ]
        if extra_info:
            message_parts.append(f"Дополнительная информация: {self._format_val(extra_info)}")
        return self._build_message(message_parts)

    def is_less_than(self, exp_value: Any, act_value: Any, extra_info: Optional[Any] = None) -> str:
        message_parts = [
            f"Ожидаемый результат: Значение в поле {self.field_name} < {self._format_val(exp_value)}",
            f"Фактический результат: {self.field_name} = {self._format_val(act_value)}",
        ]
        if extra_info:
            message_parts.append(f"Дополнительная информация: {self._format_val(extra_info)}")
        return self._build_message(message_parts)

    def is_between(self, act_value: Any, lower_bound: Any, upper_bound: Any) -> str:
        message_parts = [
            f"Ожидаемый результат: "
            f"Значение в поле {self.field_name} должно быть в диапазоне [{lower_bound}, {upper_bound}]",
            f"Фактический результат: {self.field_name} = {self._format_val(act_value)}",
        ]
        return self._build_message(message_parts)

    def does_not_contain(self, objects_list: List[ObjectType], forbidden_object: ObjectType) -> str:
        message_parts = [
            f"Ожидаемый результат: Список элементов: {objects_list}",
            f"Не содержит элемента: {forbidden_object}",
        ]
        return self._build_message(message_parts)


class StepCheck:
    """
    Обёртка для проверки
    Внутри всегда формируется единое сообщение и открывается allure.step.
    """

    def __init__(self, check_step: str, field_name: str, failures: Optional[List[str]] = None):
        # Сохраняем название проверки
        self.check_step = check_step
        self._field_name = field_name
        # Поля для хранения expected/actual/extra перед вызовом метода-проверки
        self._expected: Optional[Any] = None
        self._actual: Optional[Any] = None
        self._extra_info: Optional[str] = None
        self._msg_builder = StepMessageBuilder(check_step, field_name)
        # Хранение фейлов
        self._failures = failures

    def expected(self, value: Any) -> StepCheck:
        """Задаём ожидаемое значение и возвращаем self для цепочки вызовов"""
        self._expected = value
        return self

    def actual(self, value: Any) -> StepCheck:
        """Задаём фактическое значение и возвращаем self"""
        self._actual = value
        return self

    def extra(self, text: str) -> StepCheck:
        """Задаём дополнительный текст"""
        self._extra_info = text
        return self

    def _handle_assertion(self, exc: AssertionError) -> None:
        """
        Сохраняет traceback в список failures или перебрасывает дальше, если list не передан
        """
        if self._failures is not None:
            self._failures.append(traceback.format_exc())
        else:
            raise exc

    def equal_to(self, expected: Optional[Any] = None) -> None:
        """
        Выполняет проверку is_equal_to. Можно передать expected в метод или задать раньше через .expected(...)
        """
        # Если expected пришёл в аргументе — сохраняем его
        if expected is not None:
            self._expected = expected

        # Проверяем, что actual задан
        if self._actual is None:
            raise ValueError("Фактический результат должен быть заполнен при вызове equal_to()")

        msg = self._msg_builder.equal_to(self._expected, self._actual)

        try:
            with allure.step(msg):
                # Бросаем AssertionError в момент выполнения шага, чтобы Allure увидел failed-step
                assert_that(self._actual).described_as(msg).is_equal_to(self._expected)
        except AssertionError as exc:
            # Ловушка для исключения сразу после выхода из with - сохраняем traceback и продолжаем
            self._handle_assertion(exc)

    def is_not_equal_to(self, expected: Optional[Any] = None) -> None:
        """
        Выполняет проверку is_not_equal_to. Можно передать expected в метод или задать раньше через .expected(...)
        """
        # Если expected пришёл в аргументе — сохраняем его
        if expected is not None:
            self._expected = expected

        # Проверяем, что actual задан
        if self._actual is None:
            raise ValueError("Фактический результат должен быть заполнен при вызове is_not_equal_to()")

        msg = self._msg_builder.is_not_equal_to(self._expected, self._actual)

        try:
            with allure.step(msg):
                # Бросаем AssertionError в момент выполнения шага, чтобы Allure увидел failed-step
                assert_that(self._actual).described_as(msg).is_not_equal_to(self._expected)
        except AssertionError as exc:
            # Ловушка для исключения сразу после выхода из with - сохраняем traceback и продолжаем
            self._handle_assertion(exc)

    def is_not_none(self) -> None:
        """Проверка на существование поля"""
        if self._actual is None:
            fail("Фактический результат должен быть заполнен при вызове is_not_none()")

        msg = self._msg_builder.is_not_none(self._actual)

        try:
            with allure.step(msg):
                assert_that(self._actual).described_as(msg).is_not_none()
        except AssertionError as exc:
            # Ловушка для исключения сразу после выхода из with - сохраняем traceback и продолжаем
            self._handle_assertion(exc)

    def is_not_empty(self) -> None:
        """Проверка на не пустое значение"""
        if self._actual is None:
            fail("Фактический результат должен быть заполнен при вызове is_not_empty()")

        msg = self._msg_builder.is_not_empty(self._actual)

        try:
            with allure.step(msg):
                assert_that(self._actual).described_as(msg).is_not_empty()
        except AssertionError as exc:
            self._handle_assertion(exc)

    def is_empty(self) -> None:
        """Проверка на пустое значение"""
        if self._actual is None:
            fail("Фактический результат должен быть заполнен при вызове is_not_empty()")

        msg = self._msg_builder.is_empty(self._actual)

        try:
            with allure.step(msg):
                assert_that(self._actual).described_as(msg).is_empty()
        except AssertionError as exc:
            self._handle_assertion(exc)

    def is_close_to(self, expected: Any, allowed_diff: int | float, extra_info: Any) -> None:
        """
        Проверка допуска
        """
        if self._actual is None:
            raise ValueError("Фактический результат должен быть заполнен при вызове is_close_to()")
        self._expected = expected

        msg = self._msg_builder.is_close_to(expected, self._actual, extra_info)

        try:
            with allure.step(msg):
                assert_that(self._actual).described_as(msg).is_close_to(expected, allowed_diff)
        except AssertionError as exc:
            self._handle_assertion(exc)

    def is_less_than(self, threshold: Any, extra_info: Any) -> None:
        """Проверка, что значение меньше порога"""
        if self._actual is None:
            raise ValueError("Фактический результат должен быть заполнен при вызове is_less_than()")

        msg = self._msg_builder.is_less_than(self.check_step, self._actual, extra_info)

        try:
            with allure.step(msg):
                assert_that(self._actual).described_as(msg).is_less_than(threshold)
        except AssertionError as exc:
            self._handle_assertion(exc)

    def is_between(self, lower_bound: Any, upper_bound: Any) -> None:
        """Проверка, что значение в пределах установленных границ"""
        if self._actual is None:
            raise ValueError("Фактический результат должен быть заполнен при вызове is_less_than()")
        msg = self._msg_builder.is_between(self._actual, lower_bound, upper_bound)

        try:
            with allure.step(msg):
                assert_that(self._actual).described_as(msg).is_between(lower_bound, upper_bound)
        except AssertionError as exc:
            self._handle_assertion(exc)

    def does_not_contain(self, objects_list: List[ObjectType], forbidden_object: ObjectType) -> None:
        """
        Выполняет проверку does_not_contain.
        """

        msg = self._msg_builder.does_not_contain(objects_list, forbidden_object)

        try:
            with allure.step(msg):
                assert_that(objects_list).described_as(msg).does_not_contain(forbidden_object)
        except AssertionError as exc:
            self._handle_assertion(exc)
