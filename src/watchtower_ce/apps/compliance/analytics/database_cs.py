from django.db.models import Count, Q

from ....engine.core import ComplianceObservation, ComplianceScoreCalculator
from .. import models


def build_database_compliance_score(
    *,
    db_id: int,
    framework_ids: list[int],
) -> dict[str, object]:
    """
    Main function: computes an overall compliance score for a client database,
    considering only the LATEST version of each schema within that database.

    Returns a dictionary containing:
      - framework_scores: detailed scores per compliance framework
      - compliance_score: overall database-level score (0-100)
    """

    # Identify the latest (most recent) schema version for each unique
    # schema name. This ensures we only score the current state of each
    # schema, ignoring historical iterations.
    #
    # Ordering: by name, then descending internal_version and id.
    # We take the first row per name, which corresponds to the highest
    # version and ID.
    latest_schema_id_by_name: dict[str, int] = {}
    for row in (
        models.ClientDBSchema.objects.filter(client_db_id=db_id)
        .order_by("name", "-internal_version", "-id")
        .values("name", "id")
    ):
        if row["name"] not in latest_schema_id_by_name:
            latest_schema_id_by_name[row["name"]] = row["id"]

    # Extract just the IDs of these latest schemas for query filtering
    schema_ids = list(latest_schema_id_by_name.values())

    # Retrieve compliance frameworks (optionally filtered by the
    # provided IDs) and create a mapping from framework ID to its name.
    frameworks_qs = models.ComplianceFramework.objects.all()
    if framework_ids:
        frameworks_qs = frameworks_qs.filter(id__in=framework_ids)
    framework_map: dict[int, str] = dict(frameworks_qs.values_list("id", "name"))

    # Early exit: if there are no schemas or no frameworks to evaluate,
    # return an empty score structure.
    if not schema_ids or not framework_map:
        return {"framework_scores": {}, "compliance_score": 0.0}

    # Prepare data structures to store assertion statistics per check,
    # and to track the latest completed check for each (schema, framework).

    # Maps check_id -> {"passed": int, "total": int}
    check_stats_by_id: dict[int, dict[str, int]] = {}
    # Maps (schema_id, framework_id) -> latest check_id
    latest_check_by_schema_framework: dict[tuple[int, int], int] = {}

    # Query all valid assertions from completed checks for the target
    # database and schemas. Key differences from the iteration-based
    # function:
    # - We filter by client_db_id directly.
    # - We EXCLUDE assertions with status FAILED (they are treated as
    #   if they don't exist, rather than counting them as zero).
    # - Aggregate passed/total counts per check.
    for row in (
        models.ComplianceAssertion.objects.filter(
            compliance_check__client_db_id=db_id,
            compliance_check__schema_id__in=schema_ids,
            compliance_check__framework_id__in=list(framework_map),
            compliance_check__status=models.ComplianceCheck.Status.COMPLETED,
            result__isnull=False,
        )
        .exclude(status=models.ComplianceAssertion.Status.FAILED)
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
        # Store aggregated stats for this check
        check_stats_by_id[check_id] = {"passed": row["passed"], "total": row["total"]}

        # Update the latest check ID for this (schema, framework) pair
        key = (
            row["compliance_check__schema_id"],
            row["compliance_check__framework_id"],
        )
        current_latest = latest_check_by_schema_framework.get(key)
        if current_latest is None or check_id > current_latest:
            latest_check_by_schema_framework[key] = check_id

    # Initialize per-framework containers:
    # - A list of ComplianceObservation objects (passed/total per schema)
    # - A dictionary to accumulate total counts across all schemas for
    #   this framework (used for the final aggregated counts).
    framework_observations: dict[int, list[ComplianceObservation]] = {
        framework_id: [] for framework_id in framework_map
    }
    framework_counts: dict[int, dict[str, int]] = {
        framework_id: {
            "schema_count": 0,
            "assertions_passed": 0,
            "assertions_total": 0,
        }
        for framework_id in framework_map
    }

    # Iterate over each (schema, framework) pair that has a latest
    # completed check. For each valid check, create an observation and
    # add it to the framework's list, while also updating the aggregate
    # counts for that framework.
    for (schema_id, framework_id), check_id in latest_check_by_schema_framework.items():
        # Safety check: ensure the framework is still in our map (should always be)
        if framework_id not in framework_map:
            continue

        # Retrieve the stats for this check; skip if missing or zero total
        stats = check_stats_by_id.get(check_id)
        if stats is None or stats["total"] <= 0:
            continue

        # Create an observation representing the compliance result for this
        # specific schema under this framework
        observation = ComplianceObservation(
            passed=stats["passed"],
            total=stats["total"],
        )
        framework_observations[framework_id].append(observation)

        # Accumulate counts for the final summary
        framework_counts[framework_id]["schema_count"] += 1
        framework_counts[framework_id]["assertions_passed"] += stats["passed"]
        framework_counts[framework_id]["assertions_total"] += stats["total"]

    # Compute final scores for each framework:
    # - raw_framework_score: derived from all observations for that framework
    # - compliance_score: scaled 0-100 version of the raw score
    # - schema_weight: sum of observation weights (each observation
    #   contributes its total assertions as weight)
    # Also collect all raw framework scores to compute the overall database
    # compliance score.
    framework_scores: dict[str, dict[str, float | int]] = {}
    raw_framework_scores: list[float] = []  # used for DB-level aggregation

    for framework_id, framework_name in framework_map.items():
        observations = framework_observations[framework_id]
        counts = framework_counts[framework_id]

        # Calculate the raw compliance score for this framework across all schemas
        raw_framework_score = ComplianceScoreCalculator.framework_compliance(
            observations
        )

        # Build the detailed score dictionary for this framework
        framework_scores[framework_name] = {
            "framework_compliance": raw_framework_score,
            "compliance_score": ComplianceScoreCalculator.compliance_score(
                raw_framework_score
            ),
            "schema_weight": sum(observation.weight for observation in observations),
            "schema_count": counts["schema_count"],
            "assertions_passed": counts["assertions_passed"],
            "assertions_total": counts["assertions_total"],
        }
        # Only include frameworks with at least one valid schema in the overall average
        if counts["schema_count"] > 0:
            raw_framework_scores.append(raw_framework_score)

    # Compute the overall database-level compliance score by aggregating
    # all the raw framework scores together, then scale it to 0-100.
    overall_raw = ComplianceScoreCalculator.database_compliance(raw_framework_scores)

    # Return the final result containing per-framework details and the
    # overall database score
    return {
        "framework_scores": framework_scores,
        "compliance_score": ComplianceScoreCalculator.compliance_score(overall_raw),
    }
