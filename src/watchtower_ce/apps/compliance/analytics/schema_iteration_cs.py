from django.db.models import Count, Q

from ....engine.core import ComplianceObservation, ComplianceScoreCalculator
from .. import models

# ! I Recognise that this may not be the most efficient way to do this
# ! but we are way in over our heads in technical debt to do it cleanly
# ! and we are constrained by time. So,
# TODO: Refactor this after the backend structure is improved


def build_schema_iteration_compliance_scores(
    *,
    db_id: int,
    schema_name: str,
    framework_ids: list[int],
) -> list[dict[str, object]]:
    """
    Main function: computes compliance scores for each schema version (iteration)
    for a given client database and selected compliance frameworks.

    Returns a list of dictionaries, one per schema version, containing:
      - version: string like "v1", "v2", ...
      - framework_scores: dict mapping framework name to score details
      - compliance_score: overall compliance score (0-100)
    """

    # Fetch all schema IDs for the given client_db and schema_name,
    # ordered by internal version and ID to ensure chronological order.
    # This gives us the schema iterations (versions).
    schema_ids = list(
        models.ClientDBSchema.objects.filter(client_db_id=db_id, name=schema_name)
        .order_by("internal_version", "id")
        .values_list("id", flat=True)
    )

    # Retrieve compliance frameworks, optionally filtered by provided IDs
    frameworks_qs = models.ComplianceFramework.objects.all()
    if framework_ids:
        frameworks_qs = frameworks_qs.filter(id__in=framework_ids)
    framework_map: dict[int, str] = dict(frameworks_qs.values_list("id", "name"))

    # Early exit: if no frameworks are available, return a list of versions with empty scores and zero compliance
    if not framework_map:
        return [
            {
                "version": f"v{i + 1}",
                "framework_scores": {},
                "compliance_score": 0.0,
            }
            for i in range(len(schema_ids))
        ]

    # Prepare data structures to hold assertion statistics per check,
    # and the latest completed check ID per (schema, framework) pair.

    # Maps check_id -> {"passed": int, "total": int}
    check_execution_stats_map: dict[int, dict[str, int]] = {}
    # Maps (schema_id, framework_id) -> latest check_id that is completed
    latest_completed_check_map: dict[tuple[int, int], int] = {}

    # Query all completed checks' assertions with non-null results.
    # Aggregate passed/total counts per check using Django's Count with Q filter.
    # Also track the latest check per (schema, framework) by check ID.
    for row in (
        models.ComplianceAssertion.objects.filter(
            compliance_check__schema_id__in=schema_ids,
            compliance_check__framework_id__in=list(framework_map),
            compliance_check__status=models.ComplianceCheck.Status.COMPLETED,
            status__in=[
                models.ComplianceAssertion.Status.COMPLETED,
                models.ComplianceAssertion.Status.ANALYZING,
                models.ComplianceAssertion.Status.EXECUTING,
            ],
            result__isnull=False,
        )
        .values(
            "compliance_check_id",
            "compliance_check__schema_id",
            "compliance_check__framework_id",
        )
        .annotate(
            passed=Count("id", filter=Q(result=True)),
            total=Count("id"),
        )
    ):
        check_id = row["compliance_check_id"]
        # Store stats for this check
        check_execution_stats_map[check_id] = {
            "passed": row["passed"],
            "total": row["total"],
        }

        # Determine the latest (max ID) check for this (schema, framework)
        key = (
            row["compliance_check__schema_id"],
            row["compliance_check__framework_id"],
        )
        previous_check_id = latest_completed_check_map.get(key)
        if previous_check_id is None or check_id > previous_check_id:
            latest_completed_check_map[key] = check_id

    # Iterate over each schema version (in order) and compute scores.
    # Maintain a dictionary of the most recent valid stats per framework
    # (to carry forward if a new check is missing or invalid).
    result: list[dict[str, object]] = []
    previous_completed_stats_by_framework: dict[int, dict[str, int]] = {}
    for i, sid in enumerate(schema_ids):
        # Temporary map: framework_id -> stats for this schema version
        active_stats_by_framework: dict[int, dict[str, int]] = {}

        # For each framework, try to get stats from the latest completed
        # check for this schema. If none or total==0, fallback to the
        # previously seen stats (from an older schema version).
        for fw_id in framework_map:
            stats = None
            check_id = latest_completed_check_map.get((sid, fw_id))
            if check_id is not None:
                candidate_stats = check_execution_stats_map.get(check_id)
                if candidate_stats is not None and candidate_stats["total"] > 0:
                    stats = candidate_stats
                    # Update the "previous" stats for future schema versions
                    previous_completed_stats_by_framework[fw_id] = candidate_stats

            # Fallback to previous stats if current check is unavailable/invalid
            if stats is None:
                stats = previous_completed_stats_by_framework.get(fw_id)

            if stats is not None:
                active_stats_by_framework[fw_id] = stats

        # Build framework-level scores using the active stats.
        # Compute both raw compliance (0-1) and scaled score (0-10).
        framework_scores: dict[str, dict[str, float | int]] = {}
        raw_framework_scores: list[float] = []

        for fw_id, fw_name in framework_map.items():
            stats = active_stats_by_framework.get(fw_id)
            if stats is None:
                framework_scores[fw_name] = {
                    "schema_compliance": 0.0,
                    "compliance_score": 0.0,
                    "schema_weight": 0.0,
                    "schema_count": 0,
                    "assertions_passed": 0,
                    "assertions_total": 0,
                }
                continue

            # Create an observation (pass/total) and compute per-framework raw score
            observation = ComplianceObservation(
                passed=stats["passed"], total=stats["total"]
            )
            raw_framework_score = ComplianceScoreCalculator.framework_compliance(
                [observation]
            )
            # Store detailed info per framework
            framework_scores[fw_name] = {
                "schema_compliance": raw_framework_score,
                "compliance_score": ComplianceScoreCalculator.compliance_score(
                    raw_framework_score
                ),
                "schema_weight": observation.weight,
                "schema_count": 1,
                "assertions_passed": stats["passed"],
                "assertions_total": stats["total"],
            }
            if stats["total"] > 0:
                raw_framework_scores.append(raw_framework_score)

        # Compute overall database compliance score (aggregating all
        # frameworks for this schema version) and finalize the result entry.
        overall_raw_score = ComplianceScoreCalculator.database_compliance(
            raw_framework_scores
        )
        result.append(
            {
                "version": f"v{i + 1}",
                "framework_scores": framework_scores,
                "compliance_score": ComplianceScoreCalculator.compliance_score(
                    overall_raw_score
                ),
            }
        )

    # Return the list of versioned compliance reports
    return result
