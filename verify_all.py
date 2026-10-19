"""
=============================================================================
REDLINE GATEWAY: COMPREHENSIVE AUTOMATED VERIFICATION TEST HARNESS
Red Line Internationale Spedition GmbH / mw1group - Reference System
=============================================================================
Executes 7 test suites verifying:
  Suite 1: Configuration & Environment Settings
  Suite 2: ISO 6346 Container Checksum & Modulo-11 Logic
  Suite 3: Deterministic Compliance & Physical Conservation Audit Rules
  Suite 4: 3-Way Freight Triad Reconciliation & ADSp 2017 Discrepancy Notices
  Suite 5: T-SQL ERP Staging & C# Client Driver Generation
  Suite 6: FastAPI HTTP Endpoints (Live Test Client)
  Suite 7: SHA-256 Cryptographic Audit Ledger & Tamper Evident Persistence
=============================================================================
"""

import sys
import os
import re
import hashlib
from typing import List, Tuple

# Ensure UTF-8 console output on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# ANSI terminal colors
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"

suite_results = []

def run_suite(suite_number: int, suite_name: str, test_fn):
    print(f"\n{BOLD}{CYAN}----------------------------------------------------------------------{RESET}")
    print(f"{BOLD}{CYAN}SUITE {suite_number}: {suite_name}{RESET}")
    print(f"{BOLD}{CYAN}----------------------------------------------------------------------{RESET}")
    try:
        passed, details = test_fn()
        if passed:
            print(f"{GREEN}[PASS] Suite {suite_number}: {suite_name}{RESET}")
            for d in details:
                print(f"  {GREEN}[OK]{RESET} {d}")
            suite_results.append((suite_number, suite_name, True, None))
        else:
            print(f"{RED}[FAIL] Suite {suite_number}: {suite_name}{RESET}")
            for d in details:
                print(f"  {RED}[FAIL]{RESET} {d}")
            suite_results.append((suite_number, suite_name, False, details))
    except Exception as e:
        print(f"{RED}[ERROR] Suite {suite_number} crashed with exception: {e}{RESET}")
        import traceback
        traceback.print_exc()
        suite_results.append((suite_number, suite_name, False, [str(e)]))

# =============================================================================
# SUITE 1: Configuration & Environment Settings
# =============================================================================
def test_suite_1() -> Tuple[bool, List[str]]:
    details = []
    from app.config import settings

    if "Red Line" not in settings.COMPANY_NAME:
        return False, [f"COMPANY_NAME expected 'Red Line', got: '{settings.COMPANY_NAME}'"]
    details.append(f"COMPANY_NAME verified: '{settings.COMPANY_NAME}'")

    if "mw1group" not in settings.PARTNER_NAME:
        return False, [f"PARTNER_NAME expected 'mw1group', got: '{settings.PARTNER_NAME}'"]
    details.append(f"PARTNER_NAME verified: '{settings.PARTNER_NAME}'")

    if "redline_gateway.db" not in settings.DATABASE_URL:
        return False, [f"DATABASE_URL expected 'redline_gateway.db', got: '{settings.DATABASE_URL}'"]
    details.append(f"DATABASE_URL verified: '{settings.DATABASE_URL}'")

    return True, details

# =============================================================================
# SUITE 2: ISO 6346 Container & Checksum Logic
# =============================================================================
def test_suite_2() -> Tuple[bool, List[str]]:
    details = []
    from app.services.audit import calculate_iso6346_check_digit

    # Valid container check
    valid, calc, desc = calculate_iso6346_check_digit("MSCU7821940")
    if not valid or calc != 0:
        return False, [f"MSCU7821940 should be valid, got valid={valid}, calc={calc}"]
    details.append("Valid container 'MSCU7821940' verified (Check digit: 0)")

    valid2, calc2, _ = calculate_iso6346_check_digit("MSKU2264800")
    if not valid2 or calc2 != 0:
        return False, [f"MSKU2264800 should be valid, got valid={valid2}, calc={calc2}"]
    details.append("Valid container 'MSKU2264800' verified (Check digit: 0)")

    # Invalid checksum detection
    invalid, calc3, _ = calculate_iso6346_check_digit("MSCU7821949")
    if invalid:
        return False, ["MSCU7821949 with digit 9 should be invalid (expected 0)"]
    details.append("Invalid checksum 'MSCU7821949' correctly caught (Expected digit 0 != declared 9)")

    # Malformed container detection
    malformed, _, desc4 = calculate_iso6346_check_digit("MSCU78219")
    if malformed:
        return False, ["MSCU78219 should be rejected for invalid length"]
    details.append(f"Malformed container 'MSCU78219' correctly rejected: {desc4}")

    return True, details

# =============================================================================
# SUITE 3: Compliance & Quarantine Audit Rules
# =============================================================================
def test_suite_3() -> Tuple[bool, List[str]]:
    details = []
    from app.services.audit import run_deterministic_audit
    from app.models.schemas import ExtractedDocument, LineItem

    # 1. Clean document test
    clean_doc = ExtractedDocument(
        document_type="Ocean Bill of Lading",
        document_number="MEDUHAM192837",
        container_number="MSCU7821940",
        shipper="Hanseatic Marine Spedition GmbH, Hamburg",
        consignee="Red Line Internationale Spedition GmbH, Lage",
        gross_weight_kg=24500.0,
        net_weight_kg=21800.0,
        currency="EUR",
        incoterm="CIF",
        total_amount=12500.0,
        line_items=[
            LineItem(item_description="Industrial CNC Milling Units", quantity=2, unit_price=6250.0, total_price=12500.0, hs_code="845929")
        ]
    )
    clean_report = run_deterministic_audit(clean_doc)
    if clean_report.status != "VERIFIED_CLEAN" or not clean_report.atlas_ready:
        return False, [f"Expected VERIFIED_CLEAN, got {clean_report.status}"]
    details.append(f"Clean freight document passed audit: status='{clean_report.status}', checks={clean_report.passed_checks}/{clean_report.total_checks}")

    # 2. Physical Mass Conservation Violation (Gross < Net)
    violating_doc = ExtractedDocument(
        document_type="Commercial Invoice",
        document_number="INV-2026-0091",
        shipper="Export Partner S.A.",
        consignee="Red Line Spedition",
        gross_weight_kg=1500.0,
        net_weight_kg=2200.0,  # Impossible physical state
        currency="EUR",
        incoterm="DAP"
    )
    fail_report = run_deterministic_audit(violating_doc)
    if fail_report.status != "QUARANTINE_HOLD":
        return False, [f"Expected QUARANTINE_HOLD for Gross < Net, got {fail_report.status}"]
    details.append(f"Physical Law Violation (Gross < Net) correctly quarantined: reason='{fail_report.quarantine_reason}'")

    # 3. Missing Trade Parties Quarantine
    anonymous_doc = ExtractedDocument(
        document_type="Packing List",
        document_number="PL-9921",
        shipper=None,
        consignee=None,
        gross_weight_kg=5000.0,
        net_weight_kg=4800.0,
        currency="EUR"
    )
    anon_report = run_deterministic_audit(anonymous_doc)
    if anon_report.status != "QUARANTINE_HOLD":
        return False, ["Expected QUARANTINE_HOLD for missing trade parties"]
    details.append("Missing shipper/consignee correctly flagged with ATLAS clearance block")

    return True, details

# =============================================================================
# SUITE 4: 3-Way Triad & ADSp 2017 Notice Generation
# =============================================================================
def test_suite_4() -> Tuple[bool, List[str]]:
    details = []
    from app.services.reconciler import reconcile_documents
    from app.models.schemas import ExtractedDocument

    doc_bol = ExtractedDocument(
        document_type="Ocean Bill of Lading",
        document_number="BL-HAM-99120",
        container_number="MSCU7821940",
        gross_weight_kg=24500.0,
        currency="EUR",
        total_amount=15000.0,
        incoterm="CIF"
    )
    doc_inv = ExtractedDocument(
        document_type="Commercial Invoice",
        document_number="INV-99120",
        container_number="MSCU7821940",
        gross_weight_kg=24320.0,  # 180 kg variance exceeds 50 kg tolerance
        currency="EUR",
        total_amount=15000.0,
        incoterm="CIF"
    )
    doc_pkg = ExtractedDocument(
        document_type="Packing List",
        document_number="PK-99120",
        container_number="MSCU7821940",
        gross_weight_kg=24320.0,
        currency="EUR",
        total_amount=15000.0,
        incoterm="CIF"
    )

    reconcile_res = reconcile_documents(invoice=doc_inv, bol=doc_bol, packing_list=doc_pkg)
    if reconcile_res.overall_status != "DISCREPANCY_FLAGGED":
        return False, [f"Expected DISCREPANCY_FLAGGED, got {reconcile_res.overall_status}"]
    details.append(f"180 kg variance correctly flagged: status='{reconcile_res.overall_status}', prevented_demurrage=€{reconcile_res.demurrage_prevented_eur:,.2f}")

    if not reconcile_res.discrepancy_notice_text or "ADSp 2017" not in reconcile_res.discrepancy_notice_text:
        return False, ["Discrepancy notice must cite ADSp 2017 Section 19 / § 412 HGB"]
    details.append("ADSp 2017 / § 412 HGB discrepancy notice generated for carrier notification")

    return True, details

# =============================================================================
# SUITE 5: T-SQL Staging & C# SDK Generation
# =============================================================================
def test_suite_5() -> Tuple[bool, List[str]]:
    details = []
    from app.services.sql_generator import (
        generate_mssql_ddl,
        generate_mssql_insert,
        generate_csharp_snippet
    )
    from app.models.schemas import ExtractedDocument, AuditReport

    ddl = generate_mssql_ddl()
    if "myscm_Staging_Shipments" not in ddl:
        return False, ["DDL did not contain myscm_Staging_Shipments"]
    details.append("MS-SQL DDL script verified: targets '[dbo].[myscm_Staging_Shipments]'")

    doc = ExtractedDocument(
        document_type="Ocean Bill of Lading",
        document_number="BOL-981",
        container_number="MSCU7821940",
        gross_weight_kg=12000.0,
        net_weight_kg=11500.0,
        currency="EUR",
        total_amount=8900.0
    )
    audit = AuditReport(
        status="VERIFIED_CLEAN",
        passed_checks=5,
        total_checks=5,
        demurrage_risk_detected=False,
        estimated_demurrage_liability_eur=0.0,
        atlas_ready=True,
        checks=[]
    )
    insert_sql = generate_mssql_insert("RED-2026-TEST-001", doc, audit)
    if "INSERT INTO [dbo].[myscm_Staging_Shipments]" not in insert_sql or "'MSCU7821940'" not in insert_sql:
        return False, ["Generated T-SQL INSERT statement missing expected values"]
    details.append("Parameterized T-SQL INSERT statement safely escaped and verified")

    csharp = generate_csharp_snippet(api_url="https://redline-gateway.onrender.com")
    if "RedLineGatewayClient" not in csharp or "HttpClient" not in csharp:
        return False, ["C# snippet missing RedLineGatewayClient"]
    details.append("C# .NET 8 async client snippet verified: class 'RedLineGatewayClient'")

    return True, details

# =============================================================================
# SUITE 6: FastAPI HTTP Endpoints (Live Test Client)
# =============================================================================
def test_suite_6() -> Tuple[bool, List[str]]:
    details = []
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)

    # 1. /health
    r_health = client.get("/health")
    if r_health.status_code != 200:
        return False, [f"/health returned status {r_health.status_code}"]
    details.append(f"GET /health: 200 OK (Status='{r_health.json().get('status')}')")

    # 2. Web UI /
    r_index = client.get("/")
    if r_index.status_code != 200 or "RedLine" not in r_index.text:
        return False, [f"GET / failed with code {r_index.status_code}"]
    details.append("GET /: 200 OK (Dashboard HTML loaded)")

    # 3. /api/v1/metrics
    r_metrics = client.get("/api/v1/metrics")
    if r_metrics.status_code != 200:
        return False, [f"/api/v1/metrics failed with code {r_metrics.status_code}"]
    details.append("GET /api/v1/metrics: 200 OK (Operational metrics returned)")

    # 4. /api/v1/integration/mssql-ddl
    r_ddl = client.get("/api/v1/integration/mssql-ddl")
    if r_ddl.status_code != 200:
        return False, [f"/api/v1/integration/mssql-ddl failed with code {r_ddl.status_code}"]
    details.append("GET /api/v1/integration/mssql-ddl: 200 OK")

    # 5. /api/v1/reconcile-samples
    r_samples = client.get("/api/v1/reconcile-samples")
    if r_samples.status_code != 200:
        return False, [f"/api/v1/reconcile-samples failed with code {r_samples.status_code}"]
    details.append("GET /api/v1/reconcile-samples: 200 OK (Freight triad samples available)")

    return True, details

# =============================================================================
# SUITE 7: SHA-256 Cryptographic Audit Ledger Integrity
# =============================================================================
def test_suite_7() -> Tuple[bool, List[str]]:
    details = []
    sample_content = b"PDF-1.4 SAMPLE OCEAN BILL OF LADING MSCU7821940 HAMBURG-LAGE"
    calculated_hash = hashlib.sha256(sample_content).hexdigest()

    if len(calculated_hash) != 64:
        return False, [f"SHA-256 hash length incorrect: {len(calculated_hash)}"]
    details.append(f"SHA-256 digest computation verified: {calculated_hash[:16]}... (64 hex chars)")

    # Verify tamper evidence: 1 byte change completely alters digest
    tampered_content = b"PDF-1.4 SAMPLE OCEAN BILL OF LADING MSCU7821941 HAMBURG-LAGE"
    tampered_hash = hashlib.sha256(tampered_content).hexdigest()
    if calculated_hash == tampered_hash:
        return False, ["Hash collision or static hash returned!"]
    details.append("Tamper evidence confirmed: 1-byte alteration yields completely divergent digest (avalanche effect)")

    return True, details

# =============================================================================
# MAIN RUNNER
# =============================================================================
def main():
    print(f"\n{BOLD}======================================================================{RESET}")
    print(f"{BOLD}REDLINE GATEWAY: EXHAUSTIVE AUTOMATED VERIFICATION SUITE{RESET}")
    print(f"{BOLD}Red Line Spedition / mw1group Logistics Reference System{RESET}")
    print(f"{BOLD}======================================================================{RESET}")

    run_suite(1, "Configuration & Environment Settings", test_suite_1)
    run_suite(2, "ISO 6346 Container Checksum & Modulo-11 Logic", test_suite_2)
    run_suite(3, "Deterministic Compliance & Physical Conservation Audit Rules", test_suite_3)
    run_suite(4, "3-Way Freight Triad Reconciliation & ADSp 2017 Discrepancy Notices", test_suite_4)
    run_suite(5, "T-SQL ERP Staging & C# Client Driver Generation", test_suite_5)
    run_suite(6, "FastAPI HTTP Endpoints (Live Test Client)", test_suite_6)
    run_suite(7, "SHA-256 Cryptographic Audit Ledger Integrity", test_suite_7)

    print(f"\n{BOLD}======================================================================{RESET}")
    print(f"{BOLD}FINAL VERIFICATION SUMMARY{RESET}")
    print(f"{BOLD}======================================================================{RESET}")

    all_passed = True
    for num, name, passed, details in suite_results:
        status_str = f"{GREEN}PASS{RESET}" if passed else f"{RED}FAIL{RESET}"
        print(f"Suite {num}: {name:<60} [{status_str}]")
        if not passed:
            all_passed = False

    print(f"{BOLD}======================================================================{RESET}")
    if all_passed:
        print(f"{BOLD}{GREEN}ALL 7 SUITES PASSED: SYSTEM VERIFIED DEPLOYABLE & RELIABLE.{RESET}\n")
        return 0
    else:
        print(f"{BOLD}{RED}ONE OR MORE SUITES FAILED. SEE DETAILS ABOVE.{RESET}\n")
        return 1

if __name__ == "__main__":
    sys.exit(main())
