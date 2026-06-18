from enum import Enum


class ClauseType(str, Enum):
    INDEMNITY = "indemnity"
    LIMITATION_OF_LIABILITY = "limitation_of_liability"
    GOVERNING_LAW = "governing_law"
    TERMINATION = "termination"
    IP_OWNERSHIP = "ip_ownership"
    PAYMENT_TERMS = "payment_terms"
    CONFIDENTIALITY = "confidentiality"


ALL_CLAUSE_TYPES = list(ClauseType)

DISPLAY_NAMES = {
    ClauseType.INDEMNITY: "Indemnity",
    ClauseType.LIMITATION_OF_LIABILITY: "Limitation of Liability",
    ClauseType.GOVERNING_LAW: "Governing Law",
    ClauseType.TERMINATION: "Termination",
    ClauseType.IP_OWNERSHIP: "IP Ownership",
    ClauseType.PAYMENT_TERMS: "Payment Terms",
    ClauseType.CONFIDENTIALITY: "Confidentiality",
}
