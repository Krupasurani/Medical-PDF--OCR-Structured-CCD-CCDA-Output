"""
Variant Preservation System
Preserves original text while suggesting alternatives - NO silent correction
Contract-safe approach for medical OCR
"""

from typing import List, Dict, Optional, Set
from dataclasses import dataclass
import json
import re
from difflib import SequenceMatcher


@dataclass
class TextVariant:
    """Represents extracted text with possible alternatives"""
    raw_text: str
    alternatives: List[str]
    confidence: float
    decision: str  # 'raw_preserved', 'marked_unclear', 'multiple_variants'
    context: Optional[str] = None  # Surrounding text for disambiguation


class VariantPreservationSystem:
    """
    Preserves raw OCR output while tracking possible alternatives
    NEVER silently corrects - always preserves what was extracted
    """
    
    # Common medical term variations seen in handwriting
    KNOWN_VARIANTS = {
        'polydypsia': ['polydipsia'],
        'hypoglycemia': ['hypoglycaemia'],
        'oesophagus': ['esophagus'],
        'haemoglobin': ['hemoglobin'],
        # Add more as needed
    }
    
    def __init__(self):
        self.extraction_log: List[Dict] = []
    
    def preserve_with_variants(
        self,
        extracted_text: str,
        confidence: float,
        context: str = None
    ) -> TextVariant:
        """
        Preserve raw text and identify possible alternatives
        WITHOUT modifying the original
        """
        
        # Always keep the raw text
        raw = extracted_text.strip()
        alternatives = []
        
        # Check if this matches known variant patterns
        raw_lower = raw.lower()
        if raw_lower in self.KNOWN_VARIANTS:
            alternatives = self.KNOWN_VARIANTS[raw_lower]
        
        # Determine decision type
        if confidence < 0.70:
            decision = 'marked_unclear'
        elif alternatives:
            decision = 'multiple_variants'
        else:
            decision = 'raw_preserved'
        
        variant = TextVariant(
            raw_text=raw,
            alternatives=alternatives,
            confidence=confidence,
            decision=decision,
            context=context
        )
        
        # Log for audit trail
        self.extraction_log.append({
            'raw': raw,
            'alternatives': alternatives,
            'confidence': confidence,
            'decision': decision
        })
        
        return variant
    
    def format_for_output(
        self,
        variant: TextVariant,
        include_alternatives: bool = True
    ) -> Dict[str, any]:
        """
        Format variant for JSON output
        
        Example outputs:
        
        Good (preserves raw):
        {
            "text": "polydypsia",
            "alternatives": ["polydipsia"],
            "confidence": 0.68,
            "decision": "raw_preserved"
        }
        
        Bad (silently corrects):
        {
            "text": "polydipsia"  # ❌ NEVER DO THIS
        }
        """
        
        output = {
            "text": variant.raw_text,
            "confidence": variant.confidence,
            "decision": variant.decision
        }
        
        if include_alternatives and variant.alternatives:
            output["alternatives"] = variant.alternatives
        
        if variant.context:
            output["context"] = variant.context
        
        return output
    
    def process_medical_term(
        self,
        term: str,
        confidence: float,
        medical_dictionary: Optional[Set[str]] = None
    ) -> TextVariant:
        """
        Process a medical term while preserving the original
        Optionally check against medical dictionary for alternatives
        """
        
        alternatives = []
        
        # Check known variants first
        term_lower = term.lower()
        if term_lower in self.KNOWN_VARIANTS:
            alternatives.extend(self.KNOWN_VARIANTS[term_lower])
        
        # Check medical dictionary if provided
        if medical_dictionary and term.lower() not in medical_dictionary:
            # Find close matches
            from difflib import get_close_matches
            close = get_close_matches(
                term.lower(),
                [d.lower() for d in medical_dictionary],
                n=3,
                cutoff=0.8
            )
            alternatives.extend(close)
        
        # Remove duplicates while preserving order
        seen = set()
        alternatives = [
            x for x in alternatives 
            if x.lower() not in seen and not seen.add(x.lower())
        ]
        
        return TextVariant(
            raw_text=term,
            alternatives=alternatives,
            confidence=confidence,
            decision='multiple_variants' if alternatives else 'raw_preserved'
        )
    
    def mark_unclear_region(
        self,
        text: str,
        best_guess: Optional[str] = None,
        confidence: float = 0.5
    ) -> str:
        """
        Mark unclear text with proper formatting
        
        Returns: "[UNCLEAR: best_guess]" or "[ILLEGIBLE]"
        """
        
        if confidence < 0.3 or not best_guess:
            return "[ILLEGIBLE]"
        
        return f"[UNCLEAR: {best_guess}]"
    
    def create_audit_report(self) -> Dict[str, any]:
        """
        Create audit report showing all preservation decisions
        Useful for quality review and client transparency
        """
        
        total = len(self.extraction_log)
        
        decision_counts = {}
        for entry in self.extraction_log:
            decision = entry['decision']
            decision_counts[decision] = decision_counts.get(decision, 0) + 1
        
        avg_confidence = (
            sum(e['confidence'] for e in self.extraction_log) / total
            if total > 0 else 0.0
        )
        
        return {
            'total_terms_processed': total,
            'average_confidence': round(avg_confidence, 3),
            'decision_breakdown': decision_counts,
            'variants_identified': sum(
                1 for e in self.extraction_log 
                if e['alternatives']
            ),
            'preservation_rate': round(
                decision_counts.get('raw_preserved', 0) / total * 100, 1
            ) if total > 0 else 0.0
        }


# Example usage patterns
def example_good_preservation():
    """Show correct preservation pattern"""
    
    system = VariantPreservationSystem()
    
    # Example 1: Low confidence term
    variant1 = system.preserve_with_variants(
        extracted_text="polydypsia",
        confidence=0.68,
        context="patient has polydypsia"
    )
    
    output1 = system.format_for_output(variant1)
    print("✅ GOOD - Preserves raw text:")
    print(json.dumps(output1, indent=2))
    # Output:
    # {
    #   "text": "polydypsia",
    #   "alternatives": ["polydipsia"],
    #   "confidence": 0.68,
    #   "decision": "multiple_variants"
    # }
    
    # Example 2: Unclear text
    unclear_mark = system.mark_unclear_region(
        text="smudged",
        best_guess="hypoglycemia",
        confidence=0.55
    )
    print("\n✅ GOOD - Marks unclear:")
    print(f"  {unclear_mark}")
    # Output: "[UNCLEAR: hypoglycemia]"
    
    # Example 3: High confidence, no variants
    variant2 = system.preserve_with_variants(
        extracted_text="diabetes",
        confidence=0.95
    )
    
    output2 = system.format_for_output(variant2, include_alternatives=False)
    print("\n✅ GOOD - High confidence preserved:")
    print(json.dumps(output2, indent=2))
    # Output:
    # {
    #   "text": "diabetes",
    #   "confidence": 0.95,
    #   "decision": "raw_preserved"
    # }


def example_bad_correction():
    """Show what NOT to do"""
    
    print("\n❌ BAD - Silent correction:")
    print(json.dumps({
        "text": "polydipsia"  # Changed from "polydypsia" without noting it!
    }, indent=2))
    
    print("\nThis violates client requirement: 'Extract text as is'")


if __name__ == "__main__":
    example_good_preservation()
    example_bad_correction()