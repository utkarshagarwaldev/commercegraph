"""Provider contracts and executable plans. Schema validity is only the first gate."""

import re
from decimal import Decimal
from typing import Literal

from pydantic import model_validator

from commercegraph.dataset import Money, StrictModel

Operation = Literal[
    "find_products",
    "vendors_for_product",
    "orders_for_customer",
    "order_details",
    "customers_bought_brand",
    "vendor_product_counts",
    "lookup_value",
]
OutputMode = Literal["list", "count"]
ClarificationCode = Literal["missing_entity", "ambiguous_entity", "incomplete_question"]
UnsupportedCode = Literal["out_of_scope", "unsupported_constraint", "missing_fact"]
Template = Literal[
    "product_list",
    "product_count",
    "vendor_list",
    "customer_orders",
    "order_details",
    "customer_list",
    "vendor_counts",
    "value_matches",
    "value_count",
    "no_data",
]

RULES = {
    "find_products": (
        set(),
        {"brand_name", "vendor_name", "category_name", "price_lt_inr", "output_mode"},
    ),
    "vendors_for_product": ({"product_name"}, {"product_name"}),
    "orders_for_customer": ({"customer_name"}, {"customer_name", "order_status"}),
    "order_details": ({"order_id"}, {"order_id"}),
    "customers_bought_brand": ({"brand_name"}, {"brand_name"}),
    "vendor_product_counts": (set(), set()),
    "lookup_value": ({"value"}, {"value", "output_mode"}),
}


def to_paise(value: str) -> int:
    if not re.fullmatch(r"\d+(?:\.\d{1,2})?", value):
        raise ValueError("Price must be a nonnegative decimal string with at most two decimals")
    return int(Decimal(value) * 100)


class Parameters(StrictModel):
    brand_name: str | None
    vendor_name: str | None
    category_name: str | None
    customer_name: str | None
    product_name: str | None
    order_id: str | None
    price_lt_inr: str | None
    value: str | None
    output_mode: OutputMode | None
    order_status: Literal["delivered", "pending", "cancelled"] | None


class QueryPlan(StrictModel):
    decision: Literal["query", "clarify", "unsupported"]
    operation: Operation | None
    parameters: Parameters
    clarification_code: ClarificationCode | None
    unsupported_code: UnsupportedCode | None

    @model_validator(mode="after")
    def check_semantics(self):
        supplied = {k for k, v in self.parameters.model_dump().items() if v is not None}
        if self.decision != "query":
            if self.operation is not None or supplied:
                raise ValueError("Non-query decisions must have no operation or parameters")
            if self.decision == "clarify":
                if self.clarification_code is None or self.unsupported_code is not None:
                    raise ValueError("Clarification requires its own code only")
            elif self.unsupported_code is None or self.clarification_code is not None:
                raise ValueError("Unsupported requires its own code only")
            return self
        if self.operation is None or self.clarification_code or self.unsupported_code:
            raise ValueError("Query requires an operation and no non-query codes")
        required, allowed = RULES[self.operation]
        if not required <= supplied or supplied - allowed:
            raise ValueError("Missing required or forbidden operation parameters")
        for field in supplied - {"output_mode", "order_status", "price_lt_inr"}:
            if not getattr(self.parameters, field).strip():
                raise ValueError(f"Empty parameter: {field}")
        if self.operation == "find_products" and not supplied - {"output_mode"}:
            raise ValueError("find_products requires at least one filter")
        if self.parameters.price_lt_inr is not None:
            to_paise(self.parameters.price_lt_inr)
        return self


class ResolvedPlan(StrictModel):
    operation: Operation
    brand_id: str | None = None
    vendor_id: str | None = None
    category_id: str | None = None
    customer_id: str | None = None
    product_id: str | None = None
    order_id: str | None = None
    price_lt_paise: Money | None = None
    value: str | None = None
    output_mode: OutputMode | None = None
    order_status: Literal["delivered", "pending", "cancelled"] | None = None


class AnswerPlan(StrictModel):
    template_id: Template
    record_ids: list[str]
    aggregate_keys: list[str]


def make_query(operation: Operation, **parameters) -> QueryPlan:
    """For independently chosen deterministic fixtures, never live text routing."""
    values = dict.fromkeys(Parameters.model_fields)
    values.update(parameters)
    return QueryPlan(
        decision="query",
        operation=operation,
        parameters=Parameters(**values),
        clarification_code=None,
        unsupported_code=None,
    )
