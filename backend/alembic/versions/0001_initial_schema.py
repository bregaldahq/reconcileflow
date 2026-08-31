"""Initial reconciliation persistence schema.

Revision ID: 0001
Revises:
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "datasets",
        sa.Column("dataset_id", sa.String(length=80), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("side", sa.String(length=1), nullable=False),
        sa.Column("content_type", sa.String(length=160), nullable=False),
        sa.Column("fingerprint", sa.String(length=64), nullable=False),
        sa.Column("headers", sa.JSON(), nullable=False),
        sa.Column("rows", sa.JSON(), nullable=False),
        sa.Column("byte_size", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("side IN ('A', 'B')", name="ck_dataset_side"),
    )
    op.create_index("ix_datasets_fingerprint", "datasets", ["fingerprint"])
    op.create_table(
        "mapping_profiles",
        sa.Column("mapping_id", sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column(
            "dataset_id",
            sa.String(length=80),
            sa.ForeignKey("datasets.dataset_id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("normalization_version", sa.String(length=32), nullable=False),
        sa.Column("config", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "canonical_transactions",
        sa.Column("transaction_id", sa.String(length=255), primary_key=True),
        sa.Column(
            "dataset_id",
            sa.String(length=80),
            sa.ForeignKey("datasets.dataset_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("side", sa.String(length=1), nullable=False),
        sa.Column("amount", sa.Numeric(38, 2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("booking_date", sa.Date(), nullable=False),
        sa.Column("source_record_id", sa.String(length=255), nullable=False),
        sa.Column("document", sa.String(length=255), nullable=True),
        sa.Column("reference", sa.String(length=255), nullable=True),
        sa.CheckConstraint("side IN ('A', 'B')", name="ck_transaction_side"),
        sa.UniqueConstraint("dataset_id", "source_record_id", name="uq_transaction_source_record"),
    )
    op.create_index(
        "ix_canonical_transactions_dataset_id", "canonical_transactions", ["dataset_id"]
    )
    op.create_table(
        "rule_sets",
        sa.Column("rule_id", sa.String(length=80), primary_key=True),
        sa.Column("version", sa.String(length=40), primary_key=True),
        sa.Column("exact_fields", sa.JSON(), nullable=False),
        sa.Column("amount_tolerance", sa.Numeric(38, 2), nullable=False),
        sa.Column("date_tolerance_days", sa.Integer(), nullable=False),
        sa.Column("split_enabled", sa.Boolean(), nullable=False),
        sa.Column("max_group_size", sa.Integer(), nullable=False),
        sa.Column("max_candidate_pool", sa.Integer(), nullable=False),
        sa.Column("max_combinations", sa.Integer(), nullable=False),
        sa.CheckConstraint("amount_tolerance >= 0", name="ck_rule_amount_tolerance"),
        sa.CheckConstraint("date_tolerance_days >= 0", name="ck_rule_date_tolerance"),
        sa.CheckConstraint("max_group_size >= 2", name="ck_rule_group_size"),
        sa.CheckConstraint("max_combinations > 0", name="ck_rule_combinations"),
    )
    op.create_table(
        "reconciliation_runs",
        sa.Column("run_id", sa.String(length=80), primary_key=True),
        sa.Column(
            "dataset_a_id",
            sa.String(length=80),
            sa.ForeignKey("datasets.dataset_id"),
            nullable=False,
        ),
        sa.Column(
            "dataset_b_id",
            sa.String(length=80),
            sa.ForeignKey("datasets.dataset_id"),
            nullable=False,
        ),
        sa.Column("dataset_a_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("dataset_b_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("rule_id", sa.String(length=80), nullable=False),
        sa.Column("rule_version", sa.String(length=40), nullable=False),
        sa.Column("normalization_version", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("correlation_id", sa.String(length=100), nullable=False),
        sa.Column("idempotency_key", sa.String(length=180), nullable=False, unique=True),
        sa.Column("error_code", sa.String(length=100), nullable=True),
        sa.ForeignKeyConstraint(
            ("rule_id", "rule_version"), ("rule_sets.rule_id", "rule_sets.version")
        ),
        sa.CheckConstraint(
            "status IN ('PENDING', 'QUEUED', 'RUNNING', 'COMPLETED', 'FAILED')",
            name="ck_run_status",
        ),
        sa.UniqueConstraint("run_id", "dataset_a_id", "dataset_b_id", name="uq_run_datasets"),
    )
    op.create_index("ix_reconciliation_runs_status", "reconciliation_runs", ["status"])
    op.create_index(
        "ix_reconciliation_runs_correlation_id", "reconciliation_runs", ["correlation_id"]
    )
    op.create_table(
        "reconciliation_decisions",
        sa.Column(
            "run_id",
            sa.String(length=80),
            sa.ForeignKey("reconciliation_runs.run_id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("decision_id", sa.String(length=80), primary_key=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("rule_id", sa.String(length=80), nullable=True),
        sa.Column("rule_version", sa.String(length=40), nullable=True),
        sa.Column("confidence", sa.Numeric(12, 6), nullable=True),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.CheckConstraint(
            "status IN ('MATCHED', 'UNMATCHED', 'AMBIGUOUS', 'DUPLICATE', "
            "'MANUAL_REVIEW', 'SPLIT_MATCHED')",
            name="ck_decision_status",
        ),
        sa.CheckConstraint(
            "confidence IS NULL OR (confidence >= 0 AND confidence <= 1)",
            name="ck_decision_confidence",
        ),
        sa.CheckConstraint(
            "(rule_id IS NULL AND rule_version IS NULL) OR "
            "(rule_id IS NOT NULL AND rule_version IS NOT NULL)",
            name="ck_decision_rule_pair",
        ),
    )
    op.create_index("ix_reconciliation_decisions_status", "reconciliation_decisions", ["status"])
    op.create_table(
        "match_participants",
        sa.Column("participant_id", sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column("run_id", sa.String(length=80), nullable=False),
        sa.Column("decision_id", sa.String(length=80), nullable=False),
        sa.Column(
            "transaction_id",
            sa.String(length=255),
            sa.ForeignKey("canonical_transactions.transaction_id"),
            nullable=False,
        ),
        sa.Column("dataset_side", sa.String(length=1), nullable=False),
        sa.ForeignKeyConstraint(
            ("run_id", "decision_id"),
            ("reconciliation_decisions.run_id", "reconciliation_decisions.decision_id"),
            ondelete="CASCADE",
        ),
        sa.CheckConstraint("dataset_side IN ('A', 'B')", name="ck_participant_side"),
        sa.UniqueConstraint("run_id", "transaction_id", name="uq_run_transaction_participation"),
    )
    op.create_table(
        "manual_reviews",
        sa.Column("event_id", sa.String(length=80), primary_key=True),
        sa.Column("run_id", sa.String(length=80), nullable=False),
        sa.Column("decision_id", sa.String(length=80), nullable=False),
        sa.Column("action", sa.String(length=20), nullable=False),
        sa.Column("actor_id", sa.String(length=255), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=180), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ("run_id", "decision_id"),
            ("reconciliation_decisions.run_id", "reconciliation_decisions.decision_id"),
        ),
        sa.CheckConstraint("action IN ('APPROVE', 'REJECT')", name="ck_review_action"),
    )
    op.create_table(
        "audit_events",
        sa.Column("event_id", sa.String(length=80), primary_key=True),
        sa.Column(
            "run_id",
            sa.String(length=80),
            sa.ForeignKey("reconciliation_runs.run_id"),
            nullable=False,
        ),
        sa.Column("event_type", sa.String(length=80), nullable=False),
        sa.Column("actor_id", sa.String(length=255), nullable=False),
        sa.Column("detail", sa.Text(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=180), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_audit_events_run_id", "audit_events", ["run_id"])
    op.create_table(
        "exports",
        sa.Column("export_id", sa.String(length=80), primary_key=True),
        sa.Column(
            "run_id",
            sa.String(length=80),
            sa.ForeignKey("reconciliation_runs.run_id"),
            nullable=False,
        ),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=160), nullable=False),
        sa.Column("content", sa.LargeBinary(), nullable=False),
        sa.Column("fingerprint", sa.String(length=64), nullable=False),
        sa.Column("idempotency_key", sa.String(length=180), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_exports_run_id", "exports", ["run_id"])

    if op.get_bind().dialect.name == "postgresql":
        op.execute(
            """
            CREATE FUNCTION reconcileflow_prevent_terminal_run_update() RETURNS trigger AS $$
            BEGIN
              IF OLD.status IN ('COMPLETED', 'FAILED') THEN
                RAISE EXCEPTION 'terminal reconciliation runs are immutable';
              END IF;
              RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
            """
        )
        op.execute(
            """
            CREATE TRIGGER trg_reconcileflow_terminal_run_immutable
            BEFORE UPDATE OR DELETE ON reconciliation_runs
            FOR EACH ROW EXECUTE FUNCTION reconcileflow_prevent_terminal_run_update()
            """
        )
        op.execute(
            """
            CREATE FUNCTION reconcileflow_reject_mutation() RETURNS trigger AS $$
            BEGIN
              RAISE EXCEPTION 'append-only records cannot be updated or deleted';
            END;
            $$ LANGUAGE plpgsql;
            """
        )
        for table in (
            "reconciliation_decisions",
            "manual_reviews",
            "audit_events",
            "exports",
        ):
            op.execute(
                f"""
                CREATE TRIGGER trg_{table}_append_only
                BEFORE UPDATE OR DELETE ON {table}
                FOR EACH ROW EXECUTE FUNCTION reconcileflow_reject_mutation();
                """
            )


def downgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        for table in (
            "reconciliation_decisions",
            "manual_reviews",
            "audit_events",
            "exports",
        ):
            op.execute(f"DROP TRIGGER IF EXISTS trg_{table}_append_only ON {table}")
        op.execute(
            "DROP TRIGGER IF EXISTS trg_reconcileflow_terminal_run_immutable ON reconciliation_runs"
        )
        op.execute("DROP FUNCTION IF EXISTS reconcileflow_prevent_terminal_run_update")
        op.execute("DROP FUNCTION IF EXISTS reconcileflow_reject_mutation")
    op.drop_table("exports")
    op.drop_table("audit_events")
    op.drop_table("manual_reviews")
    op.drop_table("match_participants")
    op.drop_table("reconciliation_decisions")
    op.drop_table("reconciliation_runs")
    op.drop_table("rule_sets")
    op.drop_table("canonical_transactions")
    op.drop_table("mapping_profiles")
    op.drop_table("datasets")
