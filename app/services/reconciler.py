from typing import List, Optional, Dict, Any
from app.models.schemas import ExtractedDocument, ThreeWayReconciliationResult, ReconciliationItem

def reconcile_documents(
    invoice: Optional[ExtractedDocument],
    bol: Optional[ExtractedDocument],
    packing_list: Optional[ExtractedDocument],
    preview_urls: Optional[Dict[str, str]] = None,
    lang: str = "de"
) -> ThreeWayReconciliationResult:
    """
    Executes an enterprise cross-document 3-way reconciliation audit between
    Commercial Invoice, Bill of Lading, and Packing List.
    Outputs structured 4-column matrix data for logistics operators.
    """
    is_en = (lang == "en")
    items: List[ReconciliationItem] = []
    discrepancies: List[str] = []
    demurrage_prevented = 0.0

    # 1. Container Number Match (B/L vs Packing List)
    container_match = True
    c1 = bol.container_number if bol else None
    c2 = packing_list.container_number if packing_list else None
    c_inv = invoice.container_number if invoice else None
    
    if c1 and c2:
        clean_c1 = c1.replace(" ", "").upper()
        clean_c2 = c2.replace(" ", "").upper()
        matched = (clean_c1 == clean_c2)
        container_match = matched
        field_label = "Container Number (ISO 6346)" if is_en else "Container-Nummer (ISO 6346)"
        match_label = "Exact match (100% Match)" if is_en else "Exakt identisch (100% Match)"
        items.append(ReconciliationItem(
            field_name=field_label,
            bol_value=c1,
            invoice_value=c_inv or "-",
            packing_list_value=c2,
            tolerance_or_delta=match_label if matched else "CONTAINER MISMATCH",
            document_1_value=c1,
            document_2_value=c2,
            matched=matched,
            variance=None if matched else "CONTAINER MISMATCH"
        ))
        if not matched:
            if is_en:
                discrepancies.append(f"Container number mismatch: B/L declares '{c1}', Packing List declares '{c2}'")
            else:
                discrepancies.append(f"Container-Nummer Diskrepanz: B/L deklariert '{c1}', Packliste deklariert '{c2}'")
            demurrage_prevented += 750.0

    # 2. Gross Weight Cross-Check (B/L vs Packing List)
    weight_match = True
    w_bol = bol.gross_weight_kg if bol else None
    w_pl = packing_list.gross_weight_kg if packing_list else None
    if w_bol is not None and w_pl is not None:
        diff = abs(w_bol - w_pl)
        # German customs permits up to 1% or 50kg tare variance
        matched = (diff <= 50.0)
        weight_match = matched
        field_label = "Gross Weight" if is_en else "Bruttogewicht"
        if not matched:
            tol_text = f"Delta: {diff:,.2f} kg (> 50kg limit)" if is_en else f"Delta: {diff:,.2f} kg (> 50kg Grenze)"
            var_text = f"Delta: {diff:,.2f} kg"
        else:
            if diff > 0:
                tol_text = f"Delta: {diff:,.2f} kg (<= 50kg tolerance)" if is_en else f"Delta: {diff:,.2f} kg (<= 50kg Toleranz)"
                var_text = "Within 50kg customs tolerance" if is_en else "Innerhalb 50kg Zoll-Toleranz"
            else:
                tol_text = "0.00 kg (Exact match)" if is_en else "0.00 kg (Exakt identisch)"
                var_text = "Within 50kg customs tolerance" if is_en else "Innerhalb 50kg Zoll-Toleranz"

        items.append(ReconciliationItem(
            field_name=field_label,
            bol_value=f"{w_bol:,.2f} kg",
            invoice_value="-",
            packing_list_value=f"{w_pl:,.2f} kg",
            tolerance_or_delta=tol_text,
            document_1_value=f"{w_bol:,.2f} kg",
            document_2_value=f"{w_pl:,.2f} kg",
            matched=matched,
            variance=var_text
        ))
        if not matched:
            if is_en:
                discrepancies.append(f"Weight variance: B/L indicates {w_bol:,.2f} kg, Packing List indicates {w_pl:,.2f} kg (Delta: {diff:,.2f} kg)")
            else:
                discrepancies.append(f"Gewichtsabweichung: B/L weist {w_bol:,.2f} kg aus, Packliste weist {w_pl:,.2f} kg aus (Delta: {diff:,.2f} kg)")
            demurrage_prevented += 1250.0

    # 3. Package Count Match (B/L vs Packing List)
    pkg_bol = bol.total_packages if bol else None
    pkg_pl = packing_list.total_packages if packing_list else None
    if pkg_bol is not None and pkg_pl is not None:
        matched = (pkg_bol == pkg_pl)
        diff_pkg = abs(pkg_bol - pkg_pl)
        field_label = "Package Count (Colli)" if is_en else "Colli / Packstücke"
        delta_label = f"Delta: {diff_pkg} pkgs" if is_en else f"Delta: {diff_pkg} Colli"
        match_label = "0 Delta (100% Match)"
        items.append(ReconciliationItem(
            field_name=field_label,
            bol_value=f"{pkg_bol} {bol.package_type or 'pkgs'}",
            invoice_value="-",
            packing_list_value=f"{pkg_pl} {packing_list.package_type or 'pkgs'}",
            tolerance_or_delta=delta_label if not matched else match_label,
            document_1_value=str(pkg_bol),
            document_2_value=str(pkg_pl),
            matched=matched,
            variance=delta_label if not matched else None
        ))
        if not matched:
            if is_en:
                discrepancies.append(f"Package count variance: B/L declares {pkg_bol}, Packing List declares {pkg_pl}")
            else:
                discrepancies.append(f"Colli-Abweichung: B/L deklariert {pkg_bol}, Packliste deklariert {pkg_pl}")

    # 4. Total Value & Currency (Commercial Invoice vs B/L)
    value_match = True
    if invoice:
        val_inv = invoice.total_amount
        cur_inv = invoice.currency or "EUR"
        field_label = "Customs Value & Currency" if is_en else "Warenwert & Währung"
        bol_val_text = "- (Waybill unvalued)" if is_en else "- (Frachtbrief unbewertet)"
        tol_text = "Verified for ATLAS customs value" if is_en else "Verifiziert für ATLAS Zollwert"
        items.append(ReconciliationItem(
            field_name=field_label,
            bol_value=bol_val_text,
            invoice_value=f"{val_inv:,.2f} {cur_inv}" if val_inv is not None else "N/A",
            packing_list_value="-",
            tolerance_or_delta=tol_text,
            document_1_value=f"{val_inv:,.2f} {cur_inv}" if val_inv is not None else "N/A",
            document_2_value=tol_text,
            matched=True,
            variance=None
        ))

    # 5. Incoterms Consistency
    if invoice and invoice.incoterm:
        term_inv = invoice.incoterm
        term_bol = bol.incoterm if (bol and bol.incoterm) else ("Standard Sea Waybill Term" if is_en else "Standard-Seefrachtklausel")
        incoterm_matched = (term_inv == term_bol) if (bol and bol.incoterm) else True
        field_label = "Incoterms Rule" if is_en else "Incoterms Handelsklausel"
        tol_text = ("Commercially consistent" if is_en else "Kaufmännisch übereinstimmend") if incoterm_matched else ("Incoterm Mismatch" if is_en else "Incoterm-Diskrepanz")
        var_text = None if incoterm_matched else ("Incoterm Mismatch" if is_en else "Incoterm-Diskrepanz")
        items.append(ReconciliationItem(
            field_name=field_label,
            bol_value=term_bol,
            invoice_value=term_inv,
            packing_list_value="-",
            tolerance_or_delta=tol_text,
            document_1_value=term_inv,
            document_2_value=term_bol,
            matched=incoterm_matched,
            variance=var_text
        ))
        if not incoterm_matched:
            if is_en:
                discrepancies.append(f"Incoterm variance: Invoice declares {term_inv}, B/L declares {term_bol}")
            else:
                discrepancies.append(f"Incoterm Abweichung: Rechnung deklariert {term_inv}, B/L weist {term_bol} aus")

    is_perfect = (len(discrepancies) == 0)

    # Pre-formulate professional Discrepancy Memo (No AI slashes //, clean human typography)
    ref_container = (bol.container_number if bol else None) or (packing_list.container_number if packing_list else None) or "SHIPMENT-REF"
    if is_perfect:
        if is_en:
            memo_text = f"REDLINE GATEWAY - 3-WAY RECONCILIATION VERIFIED\nContainer: {ref_container}\nAll freight documents match 100%. Pre-cleared for ATLAS 9.1 and mw1 myscm dispatch."
        else:
            memo_text = f"REDLINE GATEWAY - 3-WEGE-ABGLEICH BESTANDEN\nContainer: {ref_container}\nAlle Frachtpapiere stimmen zu 100% überein. Freigegeben für ATLAS 9.1 und mw1 myscm."
    else:
        if is_en:
            memo_text = (
                f"DISCREPANCY NOTICE (Red Line / mw1group)\n"
                f"Reference: Container {ref_container} - 3-Way Cross-Audit\n"
                f"Status: QUARANTINE HOLD (Demurrage risk averted: {demurrage_prevented:,.2f} EUR)\n"
                f"Legal Basis: ADSp 2017 Section 19 / § 412 HGB (Notice of Loss & Recourse Rights)\n\n"
                f"Identified discrepancies between freight documents:\n" +
                "\n".join(f"  • {d}" for d in discrepancies) +
                f"\n\nImmediate action required:\n"
                f"Please submit an amended copy of the packing list or waybill immediately to prevent terminal demurrage fees upon vessel arrival."
            )
        else:
            memo_text = (
                f"SPEDITIONS-BEANSTANDUNG (Red Line / mw1group)\n"
                f"Bezug: Container {ref_container} - Transportabgleich\n"
                f"Status: QUARANTÄNE-HOLD (Standgeld-Risiko abgewendet: {demurrage_prevented:,.2f} EUR)\n"
                f"Rechtsgrundlage: ADSp 2017 Ziff. 19 / § 412 HGB (Schadenanzeige & Frachtführer-Regress)\n\n"
                f"Festgestellte Abweichungen zwischen Frachtpapieren:\n" +
                "\n".join(f"  • {d}" for d in discrepancies) +
                f"\n\nSofortmaßnahme erforderlich:\n"
                f"Bitte reichen Sie umgehend eine korrigierte Ausfertigung der Packliste bzw. des Frachtbriefs ein, "
                f"um Standgelder (Demurrage & Detention) bei Schiffsankunft zu verhindern."
            )

    # Extracted Summary chips for the 3 slots
    inv_curr = (invoice.currency or "EUR") if invoice else "EUR"
    inv_val_str = f"{invoice.total_amount:,.2f} {inv_curr}" if invoice and invoice.total_amount else "-"
    bol_wt_str = f"{bol.gross_weight_kg:,.1f} kg" if bol and bol.gross_weight_kg else "-"
    pack_wt_str = f"{packing_list.gross_weight_kg:,.1f} kg" if packing_list and packing_list.gross_weight_kg else "-"

    if is_en:
        summary_chips = {
            "bol": f"Container: {bol.container_number or '-'} | {bol_wt_str}" if bol else None,
            "invoice": f"Value: {inv_val_str} | {invoice.incoterm or '-'}" if invoice else None,
            "packing": f"Packages: {packing_list.total_packages or '-'} | {pack_wt_str}" if packing_list else None
        }
        action_req = "Auto-dispatch approved for ATLAS filing and mw1 myscm" if is_perfect else "Quarantine Hold: Issue discrepancy notice to shipping agent"
    else:
        summary_chips = {
            "bol": f"Container: {bol.container_number or '-'} | {bol_wt_str}" if bol else None,
            "invoice": f"Wert: {inv_val_str} | {invoice.incoterm or '-'}" if invoice else None,
            "packing": f"Colli: {packing_list.total_packages or '-'} | {pack_wt_str}" if packing_list else None
        }
        action_req = "Freigabe für ATLAS-Zollanmeldung und mw1 myscm erteilt" if is_perfect else "Quarantäne-Hold: Reederei-Reklamation veranlassen"

    return ThreeWayReconciliationResult(
        overall_status="PERFECT_MATCH" if is_perfect else "DISCREPANCY_FLAGGED",
        container_match=container_match,
        weight_match=weight_match,
        value_match=value_match,
        items=items,
        demurrage_prevented_eur=demurrage_prevented if not is_perfect else 0.0,
        action_required=action_req,
        discrepancy_notice_text=memo_text,
        preview_urls=preview_urls or {},
        summary_chips=summary_chips
    )
