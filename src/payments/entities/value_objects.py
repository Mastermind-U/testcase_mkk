import decimal
from dataclasses import dataclass
from typing import Self

from payments.entities.constants import CURRENCY_SCALE
from payments.entities.enums import Currency
from payments.entities.exceptions import ValidationError

type MoneyFactor = decimal.Decimal | int | float


@dataclass(slots=True, frozen=True, eq=True, unsafe_hash=True)
class Money:
    amount: decimal.Decimal
    currency: Currency = Currency.RUB

    def __post_init__(self) -> None:  # noqa: D105
        if self.currency not in CURRENCY_SCALE:
            msg = f"currency {self.currency} is not allowed"
            raise ValidationError(msg)

        if self.amount < decimal.Decimal("0"):
            msg = "money amount cannot be negative"
            raise ValidationError(msg)

        scale = CURRENCY_SCALE[self.currency]
        amount = self.amount.quantize(scale, rounding=decimal.ROUND_HALF_UP)
        object.__setattr__(self, "amount", amount)

    @classmethod
    def zero(cls, currency: Currency = Currency.RUB) -> Self:
        return cls(decimal.Decimal("0.00"), currency)

    def __composite_values__(self) -> tuple[decimal.Decimal, Currency]:  # noqa: D105
        return self.amount, self.currency

    def __add__(self, other: Money) -> Money:  # noqa: D105
        self._assert_same_currency(other)
        return Money(self.amount + other.amount, self.currency)

    def __sub__(self, other: Money) -> Money:  # noqa: D105
        self._assert_same_currency(other)
        return Money(self.amount - other.amount, self.currency)

    def __mul__(self, factor: MoneyFactor) -> Money:  # noqa: D105
        return Money(self.amount * self._as_decimal(factor), self.currency)

    def __rmul__(self, factor: MoneyFactor) -> Money:  # noqa: D105
        return self * factor

    def __truediv__(self, factor: MoneyFactor) -> Money:  # noqa: D105
        factor_amount = self._as_decimal(factor)
        if factor_amount == decimal.Decimal("0"):
            msg = "money division by zero is not allowed"
            raise ValidationError(msg)
        return Money(self.amount / factor_amount, self.currency)

    def __lt__(self, other: Money) -> bool:  # noqa: D105
        self._assert_same_currency(other)
        return self.amount < other.amount

    def __le__(self, other: Money) -> bool:  # noqa: D105
        self._assert_same_currency(other)
        return self.amount <= other.amount

    def __gt__(self, other: Money) -> bool:  # noqa: D105
        self._assert_same_currency(other)
        return self.amount > other.amount

    def __ge__(self, other: Money) -> bool:  # noqa: D105
        self._assert_same_currency(other)
        return self.amount >= other.amount

    def as_float(self) -> float:
        return float(self.amount)

    def as_int_cents(self) -> int:
        scale = CURRENCY_SCALE[self.currency]
        return int(self.amount / scale)

    def as_str(self) -> str:
        exponent = CURRENCY_SCALE[self.currency].as_tuple().exponent
        if not isinstance(exponent, int):
            msg = "money scale must be finite"
            raise ValidationError(msg)
        fractional_digits = abs(exponent)
        return f"{self.amount:.{fractional_digits}f}"

    def _assert_same_currency(self, other: Money) -> None:
        if self.currency != other.currency:
            msg = "money operations require the same currency"
            raise ValidationError(msg)

    @staticmethod
    def _as_decimal(value: MoneyFactor) -> decimal.Decimal:
        return decimal.Decimal(str(value))
