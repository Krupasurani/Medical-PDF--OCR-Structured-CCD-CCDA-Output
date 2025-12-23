"""Enumerations for medical data types"""

from enum import Enum


class DocumentType(str, Enum):
    """Type of medical document"""
    MIXED = "mixed"
    DISCHARGE_SUMMARY = "discharge_summary"
    LAB_REPORT = "lab_report"
    CONSULTATION_NOTE = "consultation_note"
    PROGRESS_NOTE = "progress_note"
    OPERATIVE_REPORT = "operative_report"


class EncounterType(str, Enum):
    """Type of clinical encounter"""
    OUTPATIENT = "outpatient"
    INPATIENT = "inpatient"
    EMERGENCY = "emergency"
    TELEHEALTH = "telehealth"
    UNKNOWN = "unknown"


class ProblemStatus(str, Enum):
    """Status of a medical problem"""
    ACTIVE = "active"
    RESOLVED = "resolved"
    CHRONIC = "chronic"
    INACTIVE = "inactive"


class AbnormalFlag(str, Enum):
    """Flag for abnormal lab/test results"""
    NORMAL = "normal"
    HIGH = "high"
    LOW = "low"
    CRITICAL = "critical"
    ABNORMAL = "abnormal"


class PlanCategory(str, Enum):
    """Category of plan/treatment action"""
    MEDICATION = "medication"
    PROCEDURE = "procedure"
    REFERRAL = "referral"
    LIFESTYLE = "lifestyle"
    FOLLOWUP = "followup"
    DIAGNOSTIC = "diagnostic"
    OTHER = "other"


class Sex(str, Enum):
    """Biological sex"""
    MALE = "M"
    FEMALE = "F"
    UNKNOWN = "U"
    OTHER = "O"


class TemperatureUnit(str, Enum):
    """Temperature units"""
    FAHRENHEIT = "F"
    CELSIUS = "C"


class VitalSignUnit(str, Enum):
    """Common vital sign units"""
    MMHG = "mmHg"
    BPM = "bpm"
    BREATHS_PER_MIN = "breaths/min"
    PERCENT = "%"
    KG = "kg"
    LBS = "lbs"
    CM = "cm"
    INCHES = "in"
