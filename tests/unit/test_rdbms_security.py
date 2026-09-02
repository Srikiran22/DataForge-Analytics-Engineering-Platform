"""Security unit tests for RDBMS identifier validation."""

import pytest

from ingestion.extractors.rdbms import _validate_identifier, extract_watermarked


def test_validate_identifier_valid_names():
    for valid_name in ["orders", "order_items", "source_oltp", "updated_at", "col1", "_hidden"]:
        _validate_identifier(valid_name)


def test_validate_identifier_rejects_sql_injection():
    for malicious in [
        "orders; DROP TABLE raw.orders;",
        "orders --",
        "orders/*comment*/",
        "orders' OR '1'='1",
        "orders union select",
        "orders; select 1",
        "schema.table",  # should be split before validating
        "123_starts_with_num",
        "orders$hack",
        "orders\nwhere 1=1",
    ]:
        with pytest.raises(ValueError, match="Invalid SQL identifier"):
            _validate_identifier(malicious)


def test_extract_watermarked_rejects_malicious_table():
    with pytest.raises(ValueError, match="Invalid SQL identifier"):
        extract_watermarked(
            dsn="dummy",
            schema="source_oltp",
            table="orders; DROP TABLE users;",
            columns=["item_id"],
            watermark_field="updated_at",
            since_value=None,
        )


def test_extract_watermarked_rejects_malicious_column():
    with pytest.raises(ValueError, match="Invalid SQL identifier"):
        extract_watermarked(
            dsn="dummy",
            schema="source_oltp",
            table="orders",
            columns=["item_id", "password FROM secrets --"],
            watermark_field="updated_at",
            since_value=None,
        )

