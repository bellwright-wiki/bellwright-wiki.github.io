from .common import (
    FieldExtractor,
    asset_reference_name,
    context_field,
    field,
    tier,
)

FIELDS: dict[str, FieldExtractor] = {
    "Category": context_field("category"),
    "Tier": tier,
    "Icon": context_field("icon"),
    "Name": field("Name"),
    "Description": field("Description"),
    "Rarity": field("Rarity", transform=asset_reference_name),
    "Expected Price": field("ExpectedPrice"),
    "Acquisition Hint": field("AcquisitionHint"),
}
