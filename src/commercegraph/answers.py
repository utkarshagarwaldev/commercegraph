"""The LLM chooses presentation references; Python supplies every factual value."""

from commercegraph.evidence import EvidenceBundle
from commercegraph.models import AnswerPlan

TEMPLATES = {
    "find_products": "product_list",
    "vendors_for_product": "vendor_list",
    "orders_for_customer": "customer_orders",
    "order_details": "order_details",
    "customers_bought_brand": "customer_list",
    "vendor_product_counts": "vendor_counts",
    "lookup_value": "value_matches",
}


def expected_template(bundle: EvidenceBundle) -> str:
    if bundle.status == "no_data":
        return "no_data"
    if bundle.query.output_mode == "count":
        return "product_count" if bundle.query.operation == "find_products" else "value_count"
    return TEMPLATES[bundle.query.operation]


def default_answer_plan(bundle: EvidenceBundle) -> AnswerPlan:
    return AnswerPlan(
        template_id=expected_template(bundle),
        record_ids=[record.record_id for record in bundle.records],
        aggregate_keys=sorted(bundle.aggregates),
    )


def validate_answer_plan(plan: AnswerPlan, bundle: EvidenceBundle) -> AnswerPlan:
    plan = AnswerPlan.model_validate(plan.model_dump())
    if plan.template_id != expected_template(bundle):
        raise ValueError("Answer template does not match query operation and status")
    expected = {record.record_id for record in bundle.records}
    if len(plan.record_ids) != len(set(plan.record_ids)) or set(plan.record_ids) != expected:
        raise ValueError("Answer references must include each retrieved record exactly once")
    if len(plan.aggregate_keys) != len(set(plan.aggregate_keys)) or set(plan.aggregate_keys) != set(
        bundle.aggregates
    ):
        raise ValueError("Answer aggregate references must match retrieved aggregates exactly")
    return plan


def money(paise: int) -> str:
    return f"INR {paise // 100:,}.{paise % 100:02}"


def render_answer(plan: AnswerPlan, bundle: EvidenceBundle) -> str:
    plan = validate_answer_plan(plan, bundle)
    count = bundle.aggregates["matching_count"]
    if plan.template_id == "no_data":
        return "No matching records in the sample graph for the interpreted filters."
    if plan.template_id in {"product_count", "value_count"}:
        entity = "distinct products" if plan.template_id == "product_count" else "graph markers"
        return f"Found {count} matching {entity} in the sample graph."
    by_id = {record.record_id: record for record in bundle.records}
    lines = []
    for record_id in plan.record_ids:
        record = by_id[record_id]
        f = record.fields
        if plan.template_id == "product_list":
            lines.append(
                f"{f['id']} · {f['name']} — {money(f['price_paise'])} "
                f"({f['brand']}; {f['category']})"
            )
        elif plan.template_id == "vendor_list":
            lines.append(
                f"{f['id']} · {f['name']} supplies {f['product_name']} "
                f"({f['product_id']}) in the catalog."
            )
        elif plan.template_id in {"customer_orders", "order_details"}:
            lines.append(
                f"{f['id']} · {f['status']} · {f['date']} · "
                f"{f['customer_name']} — merchandise total {money(f['total_paise'])}"
            )
            if plan.template_id == "order_details":
                for item in f["items"]:
                    lines.append(
                        f"  {item['item_id']} · {item['product_name']}: "
                        f"{item['quantity']} × {money(item['unit_price_paise'])} "
                        f"= {money(item['line_total_paise'])}"
                    )
                lines.append("Merchandise total only; tax and shipping are not modeled.")
        elif plan.template_id == "customer_list":
            lines.append(
                f"{f['id']} · {f['name']} — delivered orders: "
                + ", ".join(f["delivered_order_ids"])
            )
        elif plan.template_id == "vendor_counts":
            lines.append(
                f"{f['id']} · {f['name']}: {f['product_count']} distinct supplied products"
            )
        elif plan.template_id == "value_matches":
            lines.append(
                f"{f['id']} · value '{f['value']}' → {f['product_id']} · {f['product_name']}"
            )
    noun = "record" if count == 1 else "records"
    heading = f"Found {count} matching {noun} in the sample graph."
    if plan.template_id == "customer_list":
        heading += " Purchases include delivered orders only."
    if plan.template_id == "value_matches":
        heading += " These are artificial assignment markers."
    return "\n".join([heading, *lines])
