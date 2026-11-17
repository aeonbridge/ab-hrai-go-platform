"""Minimal LegalAssessmentEngine.

Determines finding status from source legal status and available evidence
only. The council never writes here (no finding derives from synthetic votes).
Requirement decomposition (SHACL/normative rules) is out of scope for this
runtime; effective sources therefore yield ``insufficientEvidence`` or
``requiresLegalReview`` instead of substantive conclusions.
"""
from __future__ import annotations

STATUS_MAP = {
    "proposed": "proposalOnly",
    "enactedNotEffective": "futureObligation",
    "repealed": "notApplicable",
    "superseded": "notApplicable",
    "suspended": "requiresLegalReview",
    "unknown": "requiresLegalReview",
}


def assess(scenario: dict) -> list[dict]:
    findings = []
    solution = scenario.get("solution") or {}
    evidence = solution.get("evidenceIds", [])
    for i, src in enumerate(scenario.get("regulatorySources", []), start=1):
        status = src["status"]
        requirement = f"{src['id']}:applicability"
        if status in STATUS_MAP:
            fstatus = STATUS_MAP[status]
            rationale = {
                "proposalOnly": "Instrumento em tramitação; usado apenas como cenário prospectivo (FR-08).",
                "futureObligation": "Aprovado, mas não exigível na data de referência.",
                "notApplicable": f"Fonte declarada como {status} na data de referência.",
                "requiresLegalReview": f"Status declarado '{status}' exige verificação humana antes de qualquer conclusão.",
            }[fstatus]
        elif scenario["mode"] == "solutionCompliance":
            fstatus = "requiresLegalReview" if evidence else "insufficientEvidence"
            rationale = ("Norma declarada vigente; decomposição de requisitos e mapeamento de evidências pendentes "
                         "de revisão humana." if evidence else
                         "Norma declarada vigente, mas nenhuma evidência da solução foi fornecida; ausência de "
                         "documento não prova violação.")
        else:
            fstatus = "requiresLegalReview"
            rationale = ("Modo de política: a fonte vigente contextualiza a deliberação; conclusões de conformidade "
                         "não são emitidas neste modo.")
        findings.append({"id": f"F{i:03d}", "requirementId": requirement, "status": fstatus,
                         "legalSourceIds": [src["id"]], "evidenceIds": list(evidence) if status == "effective" else [],
                         "rationale": rationale, "reviewedByHuman": False})
    return findings
