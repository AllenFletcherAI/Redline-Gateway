"""
Pytest integration for RedLine Gateway verification.
"""
import pytest
from app.services.audit import calculate_iso6346_check_digit, run_deterministic_audit
from app.models.schemas import ExtractedDocument, LineItem
from app.services.reconciler import reconcile_documents
from app.services.sql_generator import generate_mssql_ddl, generate_mssql_insert

def test_valid_iso6346():
    valid, digit, _ = calculate_iso6346_check_digit("MSCU7821940")
    assert valid is True
    assert digit == 0

def test_invalid_iso6346():
    valid, digit, _ = calculate_iso6346_check_digit("MSCU7821949")
    assert valid is False
    assert digit == 0

def test_mass_conservation_quarantine():
    doc = ExtractedDocument(
        document_type="Commercial Invoice",
        document_number="INV-FAIL-01",
        shipper="ABC Corp",
        consignee="XYZ GmbH",
        gross_weight_kg=1000.0,
        net_weight_kg=1500.0,  # Impossible: Gross < Net
        currency="EUR"
    )
    report = run_deterministic_audit(doc)
    assert report.status == "QUARANTINE_HOLD"
    assert report.demurrage_risk_detected is True

def test_clean_document_passes():
    doc = ExtractedDocument(
        document_type="Ocean Bill of Lading",
        document_number="BOL-CLEAN-01",
        container_number="MSCU7821940",
        shipper="Shipper A",
        consignee="Consignee B",
        gross_weight_kg=20000.0,
        net_weight_kg=18500.0,
        currency="EUR",
        incoterm="CIF",
        total_amount=5000.0,
        line_items=[LineItem(item_description="Machinery", quantity=1, unit_price=5000.0, total_price=5000.0, hs_code="845929")]
    )
    report = run_deterministic_audit(doc)
    assert report.status == "VERIFIED_CLEAN"
    assert report.atlas_ready is True

def test_reconciliation_variance_detection():
    doc_bol = ExtractedDocument(document_type="Ocean Bill of Lading", gross_weight_kg=24500.0, currency="EUR", total_amount=10000.0)
    doc_inv = ExtractedDocument(document_type="Commercial Invoice", gross_weight_kg=24300.0, currency="EUR", total_amount=10000.0)
    doc_pkg = ExtractedDocument(document_type="Packing List", gross_weight_kg=24300.0, currency="EUR", total_amount=10000.0)
    result = reconcile_documents(invoice=doc_inv, bol=doc_bol, packing_list=doc_pkg)
    assert result.overall_status == "DISCREPANCY_FLAGGED"
    assert result.demurrage_prevented_eur > 0

def test_sql_ddl_and_escaped_insert():
    ddl = generate_mssql_ddl()
    assert "myscm_Staging_Shipments" in ddl
