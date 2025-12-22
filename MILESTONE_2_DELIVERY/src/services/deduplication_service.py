"""Deduplication and merge service

Implements exact and fuzzy matching logic to deduplicate and merge
medical data across visits and pages.

Follows LLM_TECHNICAL_SPEC.md Section 8: Deduplication & Merge Rules
"""

from typing import List, Dict, Any, Tuple
from difflib import SequenceMatcher
import re

from ..utils.logger import get_logger

logger = get_logger(__name__)


class DeduplicationService:
    """Handle deduplication and merging of medical data"""

    def __init__(self, fuzzy_threshold: float = 0.85):
        """Initialize deduplication service

        Args:
            fuzzy_threshold: Similarity threshold for fuzzy matching (default: 0.85)
        """
        self.fuzzy_threshold = fuzzy_threshold
        logger.info("Deduplication service initialized", fuzzy_threshold=fuzzy_threshold)

    def normalize_text(self, text: str) -> str:
        """Normalize text for comparison

        Args:
            text: Raw text string

        Returns:
            Normalized text (lowercase, whitespace normalized)
        """
        if not text:
            return ""

        # Convert to lowercase
        normalized = text.lower()

        # Normalize whitespace
        normalized = re.sub(r'\s+', ' ', normalized).strip()

        return normalized

    def calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two strings using Levenshtein-based ratio

        Args:
            text1: First string
            text2: Second string

        Returns:
            Similarity score between 0.0 and 1.0
        """
        norm1 = self.normalize_text(text1)
        norm2 = self.normalize_text(text2)

        if not norm1 or not norm2:
            return 0.0

        # Use SequenceMatcher for fuzzy string matching
        return SequenceMatcher(None, norm1, norm2).ratio()

    def is_exact_match(self, text1: str, text2: str) -> bool:
        """Check if two texts are exact matches (after normalization)

        Args:
            text1: First string
            text2: Second string

        Returns:
            True if exact match, False otherwise
        """
        return self.normalize_text(text1) == self.normalize_text(text2)

    def is_fuzzy_match(self, text1: str, text2: str) -> Tuple[bool, float]:
        """Check if two texts are fuzzy matches

        Args:
            text1: First string
            text2: Second string

        Returns:
            Tuple of (is_match, similarity_score)
        """
        similarity = self.calculate_similarity(text1, text2)
        return (similarity >= self.fuzzy_threshold, similarity)

    def merge_medications(self, medications: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Deduplicate and merge medications

        Strategy:
        - Exact match on name → merge if same dose, keep separate if different
        - Fuzzy match → merge and prefer more complete entry
        - Track all source pages

        Args:
            medications: List of medication entries

        Returns:
            Deduplicated list of medications
        """
        if not medications:
            return []

        logger.info("Deduplicating medications", total=len(medications))

        merged = []
        processed_indices = set()

        for i, med1 in enumerate(medications):
            if i in processed_indices:
                continue

            # Start with current medication
            base_med = med1.copy()
            source_pages = set([med1.get("source_page")])
            matched_indices = {i}

            # Find duplicates
            for j, med2 in enumerate(medications[i+1:], start=i+1):
                if j in processed_indices:
                    continue

                name1 = med1.get("name", "")
                name2 = med2.get("name", "")

                # Exact match
                if self.is_exact_match(name1, name2):
                    # Merge data (prefer more complete)
                    base_med = self._merge_medication_entries(base_med, med2)
                    source_pages.add(med2.get("source_page"))
                    matched_indices.add(j)
                    logger.debug("Exact medication match", name=name1, pages=list(source_pages))

                # Fuzzy match
                else:
                    is_match, similarity = self.is_fuzzy_match(name1, name2)
                    if is_match:
                        logger.debug(
                            "Fuzzy medication match",
                            name1=name1,
                            name2=name2,
                            similarity=round(similarity, 2)
                        )
                        base_med = self._merge_medication_entries(base_med, med2)
                        base_med.setdefault("alternative_representations", [])
                        if name2 not in base_med["alternative_representations"]:
                            base_med["alternative_representations"].append(name2)
                        source_pages.add(med2.get("source_page"))
                        matched_indices.add(j)

            # Update source pages
            base_med["source_pages"] = sorted(list(source_pages))
            if len(source_pages) > 1:
                base_med["merge_confidence"] = 0.95  # High confidence for medication merges

            merged.append(base_med)
            processed_indices.update(matched_indices)

        logger.info(
            "Medication deduplication complete",
            original=len(medications),
            deduplicated=len(merged),
            reduction=len(medications) - len(merged)
        )

        return merged

    def _merge_medication_entries(
        self,
        base: Dict[str, Any],
        other: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Merge two medication entries, preferring more complete data

        Args:
            base: Base medication entry
            other: Other medication entry to merge

        Returns:
            Merged medication entry
        """
        merged = base.copy()

        # Prefer more complete values
        for key in ["dose", "frequency", "route", "start_date", "end_date"]:
            if not merged.get(key) and other.get(key):
                merged[key] = other[key]
            elif merged.get(key) and other.get(key) and merged[key] != other[key]:
                # Conflict detected - use first, note alternative
                merged.setdefault("value_conflicts", {})
                merged["value_conflicts"][key] = [merged[key], other[key]]

        return merged

    def merge_problems(self, problems: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Deduplicate and merge problem list entries

        Strategy:
        - Exact match on problem text → merge
        - Fuzzy match → merge and track alternatives
        - Track all source pages

        Args:
            problems: List of problem entries

        Returns:
            Deduplicated list of problems
        """
        if not problems:
            return []

        logger.info("Deduplicating problems", total=len(problems))

        merged = []
        processed_indices = set()

        for i, prob1 in enumerate(problems):
            if i in processed_indices:
                continue

            base_problem = prob1.copy()
            source_pages = set([prob1.get("source_page")])
            matched_indices = {i}

            for j, prob2 in enumerate(problems[i+1:], start=i+1):
                if j in processed_indices:
                    continue

                text1 = prob1.get("problem", "")
                text2 = prob2.get("problem", "")

                # Exact match
                if self.is_exact_match(text1, text2):
                    base_problem = self._merge_problem_entries(base_problem, prob2)
                    source_pages.add(prob2.get("source_page"))
                    matched_indices.add(j)
                    logger.debug("Exact problem match", problem=text1, pages=list(source_pages))

                # Fuzzy match
                else:
                    is_match, similarity = self.is_fuzzy_match(text1, text2)
                    if is_match:
                        logger.debug(
                            "Fuzzy problem match",
                            problem1=text1,
                            problem2=text2,
                            similarity=round(similarity, 2)
                        )
                        # Prefer more complete representation
                        if len(text2) > len(text1):
                            base_problem["problem"] = text2
                            base_problem.setdefault("alternative_representations", [])
                            if text1 not in base_problem["alternative_representations"]:
                                base_problem["alternative_representations"].append(text1)
                        else:
                            base_problem.setdefault("alternative_representations", [])
                            if text2 not in base_problem["alternative_representations"]:
                                base_problem["alternative_representations"].append(text2)

                        base_problem = self._merge_problem_entries(base_problem, prob2)
                        source_pages.add(prob2.get("source_page"))
                        matched_indices.add(j)

            base_problem["source_pages"] = sorted(list(source_pages))
            merged.append(base_problem)
            processed_indices.update(matched_indices)

        logger.info(
            "Problem deduplication complete",
            original=len(problems),
            deduplicated=len(merged),
            reduction=len(problems) - len(merged)
        )

        return merged

    def _merge_problem_entries(
        self,
        base: Dict[str, Any],
        other: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Merge two problem entries

        Args:
            base: Base problem entry
            other: Other problem entry to merge

        Returns:
            Merged problem entry
        """
        merged = base.copy()

        # Prefer values from either entry (non-null)
        for key in ["icd10_code", "status", "onset_date"]:
            if not merged.get(key) and other.get(key):
                merged[key] = other[key]

        return merged

    def merge_lab_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Deduplicate and merge lab results

        Strategy:
        - Match on test name (exact or fuzzy)
        - If same value → merge
        - If different values → keep both, flag conflict
        - Track all source pages

        Args:
            results: List of lab result entries

        Returns:
            Deduplicated list of results
        """
        if not results:
            return []

        logger.info("Deduplicating lab results", total=len(results))

        merged = []
        processed_indices = set()

        for i, result1 in enumerate(results):
            if i in processed_indices:
                continue

            base_result = result1.copy()
            source_pages = set([result1.get("source_page")])
            matched_indices = {i}

            for j, result2 in enumerate(results[i+1:], start=i+1):
                if j in processed_indices:
                    continue

                test1 = result1.get("test_name", "")
                test2 = result2.get("test_name", "")

                # Check if same test
                is_same_test = False
                if self.is_exact_match(test1, test2):
                    is_same_test = True
                else:
                    is_match, similarity = self.is_fuzzy_match(test1, test2)
                    if is_match:
                        is_same_test = True
                        logger.debug(
                            "Fuzzy test name match",
                            test1=test1,
                            test2=test2,
                            similarity=round(similarity, 2)
                        )

                if is_same_test:
                    # Check if same value
                    val1 = str(result1.get("value", ""))
                    val2 = str(result2.get("value", ""))

                    if self.is_exact_match(val1, val2):
                        # Same test, same value → merge
                        base_result = self._merge_lab_result_entries(base_result, result2)
                        source_pages.add(result2.get("source_page"))
                        matched_indices.add(j)
                    else:
                        # Same test, different values → flag conflict
                        logger.warning(
                            "Lab result value conflict",
                            test=test1,
                            value1=val1,
                            value2=val2,
                            pages=[result1.get("source_page"), result2.get("source_page")]
                        )
                        base_result.setdefault("value_conflicts", [])
                        base_result["value_conflicts"].append({
                            "value": val2,
                            "unit": result2.get("unit"),
                            "source_page": result2.get("source_page")
                        })
                        source_pages.add(result2.get("source_page"))
                        matched_indices.add(j)

            base_result["source_pages"] = sorted(list(source_pages))
            if len(source_pages) > 1:
                base_result["merge_confidence"] = 0.95

            merged.append(base_result)
            processed_indices.update(matched_indices)

        logger.info(
            "Lab result deduplication complete",
            original=len(results),
            deduplicated=len(merged),
            reduction=len(results) - len(merged)
        )

        return merged

    def _merge_lab_result_entries(
        self,
        base: Dict[str, Any],
        other: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Merge two lab result entries

        Args:
            base: Base result entry
            other: Other result entry to merge

        Returns:
            Merged result entry
        """
        merged = base.copy()

        # Prefer more complete data
        for key in ["unit", "reference_range", "abnormal_flag", "test_date"]:
            if not merged.get(key) and other.get(key):
                merged[key] = other[key]

        return merged

    def deduplicate_visit(self, visit: Dict[str, Any]) -> Dict[str, Any]:
        """Deduplicate data within a single visit

        Args:
            visit: Visit data dictionary

        Returns:
            Visit with deduplicated data
        """
        deduplicated = visit.copy()

        # Deduplicate medications
        if "medications" in deduplicated and deduplicated["medications"]:
            deduplicated["medications"] = self.merge_medications(deduplicated["medications"])

        # Deduplicate problems
        if "problem_list" in deduplicated and deduplicated["problem_list"]:
            deduplicated["problem_list"] = self.merge_problems(deduplicated["problem_list"])

        # Deduplicate lab results
        if "results" in deduplicated and deduplicated["results"]:
            deduplicated["results"] = self.merge_lab_results(deduplicated["results"])

        return deduplicated

    def deduplicate_document(self, visits: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Deduplicate data across all visits in a document

        Args:
            visits: List of visit dictionaries

        Returns:
            List of visits with deduplicated data
        """
        logger.info("Deduplicating document", total_visits=len(visits))

        # First, deduplicate within each visit
        deduplicated_visits = [self.deduplicate_visit(visit) for visit in visits]

        logger.info("Document deduplication complete", total_visits=len(deduplicated_visits))

        return deduplicated_visits
