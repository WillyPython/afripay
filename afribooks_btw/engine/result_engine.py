from dataclasses import dataclass


@dataclass
class OperatingResult:
    operating_revenue: float
    operating_expenses: float
    operating_result: float
    status: str


def calculate_operating_result(
    operating_revenue: float = 0.0,
    operating_expenses: float = 0.0,
) -> OperatingResult:
    revenue = float(operating_revenue or 0.0)
    expenses = abs(float(operating_expenses or 0.0))
    result = revenue - expenses

    if result > 0:
        status = "PROFIT"
    elif result < 0:
        status = "LOSS"
    else:
        status = "BREAK_EVEN"

    return OperatingResult(
        operating_revenue=round(revenue, 2),
        operating_expenses=round(expenses, 2),
        operating_result=round(result, 2),
        status=status,
    )

