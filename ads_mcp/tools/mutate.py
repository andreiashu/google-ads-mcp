"""Tools for mutating Google Ads resources via the MCP server."""

from typing import Any, Dict, List, Optional
from ads_mcp.coordinator import mcp
import ads_mcp.utils as utils


@mcp.tool()
def update_campaign_setting(
    customer_id: str,
    campaign_id: str,
    field_path: str,
    value: str,
) -> Dict[str, Any]:
    """Updates a single field on a campaign.

    Args:
        customer_id: The customer ID (digits only, no hyphens).
        campaign_id: The campaign ID to update.
        field_path: Dotted field path to update (e.g. 'geo_target_type_setting.positive_geo_target_type').
        value: The new value. For enums use the enum name (e.g. 'PRESENCE', 'PRESENCE_OR_INTEREST').

    Common field_path + value examples:
        - geo_target_type_setting.positive_geo_target_type = PRESENCE | PRESENCE_OR_INTEREST
        - geo_target_type_setting.negative_geo_target_type = PRESENCE | PRESENCE_OR_INTEREST
        - network_settings.target_search_network = true | false
        - network_settings.target_content_network = true | false
        - status = ENABLED | PAUSED | REMOVED
    """
    client = utils.get_googleads_client()
    campaign_service = client.get_service("CampaignService")

    operation = client.get_type("CampaignOperation")
    campaign = operation.update
    campaign.resource_name = campaign_service.campaign_path(
        customer_id, campaign_id
    )

    # Navigate dotted path and set the value
    _set_proto_field(client, campaign, field_path, value)
    operation.update_mask.paths.append(field_path)

    response = campaign_service.mutate_campaigns(
        customer_id=customer_id, operations=[operation]
    )

    return {
        "success": True,
        "resource_name": response.results[0].resource_name,
        "field_updated": field_path,
        "new_value": value,
    }


@mcp.tool()
def update_conversion_action(
    customer_id: str,
    conversion_action_id: str,
    counting_type: Optional[str] = None,
    default_value: Optional[float] = None,
    default_currency_code: Optional[str] = None,
) -> Dict[str, Any]:
    """Updates a conversion action's counting type and/or default value settings.

    Args:
        customer_id: The customer ID (digits only, no hyphens).
        conversion_action_id: The conversion action ID to update.
        counting_type: ONE_PER_CLICK or MANY_PER_CLICK. ONE_PER_CLICK counts at most one conversion per click.
        default_value: The default monetary value for each conversion (e.g. 8670.0).
        default_currency_code: Currency code for the value (e.g. 'THB', 'USD').
    """
    client = utils.get_googleads_client()
    ca_service = client.get_service("ConversionActionService")

    operation = client.get_type("ConversionActionOperation")
    ca = operation.update
    ca.resource_name = ca_service.conversion_action_path(
        customer_id, conversion_action_id
    )

    update_paths = []

    if counting_type is not None:
        ca.counting_type = getattr(
            client.enums.ConversionActionCountingTypeEnum, counting_type
        )
        update_paths.append("counting_type")

    if default_value is not None:
        ca.value_settings.default_value = default_value
        update_paths.append("value_settings.default_value")

    if default_currency_code is not None:
        ca.value_settings.default_currency_code = default_currency_code
        update_paths.append("value_settings.default_currency_code")

    if not update_paths:
        return {"success": False, "error": "No fields to update."}

    operation.update_mask.paths.extend(update_paths)

    response = ca_service.mutate_conversion_actions(
        customer_id=customer_id, operations=[operation]
    )

    return {
        "success": True,
        "resource_name": response.results[0].resource_name,
        "fields_updated": update_paths,
    }


@mcp.tool()
def add_negative_keywords(
    customer_id: str,
    campaign_id: str,
    keywords: List[str],
    match_type: str = "BROAD",
) -> Dict[str, Any]:
    """Adds negative keywords to a campaign.

    Args:
        customer_id: The customer ID (digits only, no hyphens).
        campaign_id: The campaign ID to add negatives to.
        keywords: List of keyword texts to add as negatives.
        match_type: BROAD, PHRASE, or EXACT. Default BROAD (blocks widest range of queries).

    Example:
        add_negative_keywords('1234567890', '111222333', ['free', 'cheap', 'DIY'], 'BROAD')
    """
    client = utils.get_googleads_client()
    campaign_service = client.get_service("CampaignService")
    cc_service = client.get_service("CampaignCriterionService")

    campaign_rn = campaign_service.campaign_path(customer_id, campaign_id)
    kw_match = getattr(client.enums.KeywordMatchTypeEnum, match_type)

    operations = []
    for kw_text in keywords:
        operation = client.get_type("CampaignCriterionOperation")
        criterion = operation.create
        criterion.campaign = campaign_rn
        criterion.negative = True
        criterion.keyword.text = kw_text
        criterion.keyword.match_type = kw_match
        operations.append(operation)

    response = cc_service.mutate_campaign_criteria(
        customer_id=customer_id, operations=operations
    )

    return {
        "success": True,
        "keywords_added": len(response.results),
        "match_type": match_type,
        "campaign_id": campaign_id,
    }


@mcp.tool()
def create_conversion_action(
    customer_id: str,
    name: str,
    category: str = "SUBMIT_LEAD_FORM",
    counting_type: str = "ONE_PER_CLICK",
    default_value: float = 0.0,
    default_currency_code: str = "THB",
    click_through_lookback_window_days: int = 30,
) -> Dict[str, Any]:
    """Creates a new conversion action.

    Args:
        customer_id: The customer ID (digits only, no hyphens).
        name: Name for the conversion action (e.g. 'Partner Agent Lead').
        category: Conversion category. Common: SUBMIT_LEAD_FORM, PURCHASE, SIGNUP, DEFAULT.
        counting_type: ONE_PER_CLICK or MANY_PER_CLICK.
        default_value: Default monetary value per conversion.
        default_currency_code: Currency code (e.g. 'THB', 'USD').
        click_through_lookback_window_days: Days to attribute conversions after click (1-90, default 30).
    """
    client = utils.get_googleads_client()
    ca_service = client.get_service("ConversionActionService")

    operation = client.get_type("ConversionActionOperation")
    ca = operation.create
    ca.name = name
    ca.type_ = client.enums.ConversionActionTypeEnum.WEBPAGE
    ca.category = getattr(client.enums.ConversionActionCategoryEnum, category)
    ca.counting_type = getattr(
        client.enums.ConversionActionCountingTypeEnum, counting_type
    )
    ca.value_settings.default_value = default_value
    ca.value_settings.default_currency_code = default_currency_code
    ca.value_settings.always_use_default_value = True
    ca.click_through_lookback_window_days = click_through_lookback_window_days
    ca.status = client.enums.ConversionActionStatusEnum.ENABLED

    response = ca_service.mutate_conversion_actions(
        customer_id=customer_id, operations=[operation]
    )

    result = response.results[0]
    return {
        "success": True,
        "resource_name": result.resource_name,
        "name": name,
    }


def _set_proto_field(client, proto_obj, field_path: str, value: str):
    """Sets a value on a protobuf object given a dotted field path.

    Handles enum resolution automatically for known Google Ads enum fields.
    """
    parts = field_path.split(".")
    obj = proto_obj

    # Navigate to parent of the leaf field
    for part in parts[:-1]:
        obj = getattr(obj, part)

    leaf = parts[-1]

    # Try to resolve as enum first
    if value in ("true", "false"):
        setattr(obj, leaf, value == "true")
    else:
        try:
            # Attempt to set as-is (works for strings, numbers)
            current = getattr(obj, leaf)
            if isinstance(current, int) and not isinstance(current, bool):
                setattr(obj, leaf, int(value))
            elif isinstance(current, float):
                setattr(obj, leaf, float(value))
            else:
                # For enums, try setting the string name directly
                # proto-plus handles enum name -> value conversion
                setattr(obj, leaf, value)
        except (ValueError, AttributeError):
            setattr(obj, leaf, value)
