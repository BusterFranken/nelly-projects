from admin_automator.extract import extract_fields_from_text


def test_extract_fields_basic_invoice():
    text = """
    ACME Consulting BV
    Invoice Date: 2026-02-01
    Invoice No: INV-1001

    Subtotal € 100,00
    VAT 21% € 21,00
    Total Due € 121,00

    KvK: 12345678
    VAT No: NL123456789B01
    """.strip()

    f = extract_fields_from_text(text, vendor_hint=None)
    assert f.invoice_date == "2026-02-01"
    assert f.total == "121.00"
    assert f.vat_amount == "21.00"
    assert f.vendor == "ACME Consulting BV"
    assert f.vat_numbers and any("NL123456789B01" in x.replace(" ", "") for x in f.vat_numbers)
    assert f.company_numbers and any("12345678" in x for x in f.company_numbers)


def test_extract_fields_fallback_total_max_amount():
    text = """
    Something
    Line item 1: € 10,00
    Line item 2: € 200,00
    """.strip()

    f = extract_fields_from_text(text)
    assert f.total == "200.00"
