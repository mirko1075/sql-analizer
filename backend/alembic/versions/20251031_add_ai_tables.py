"""Add AI analysis tables and metadata cache.

Revision ID: 20251031_add_ai_tables
Revises: None
Create Date: 2025-10-31
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "20251031_add_ai_tables"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():  # noqa: D401
    """Add AI analysis support structures."""
    op.create_table(
        "db_metadata_cache",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("source_db_type", sa.String(length=20), nullable=False),
        sa.Column("source_db_host", sa.String(length=255), nullable=False),
        sa.Column("source_db_name", sa.String(length=100), nullable=False),
        sa.Column("tables", postgresql.JSONB, nullable=True),
        sa.Column("indexes", postgresql.JSONB, nullable=True),
        sa.Column("statistics", postgresql.JSONB, nullable=True),
        sa.Column("configuration", postgresql.JSONB, nullable=True),
        sa.Column("relations", postgresql.JSONB, nullable=True),
        sa.Column("collected_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.UniqueConstraint(
            "source_db_type",
            "source_db_host",
            "source_db_name",
            name="unique_db_metadata_cache_source",
        ),
    )
    op.create_index(
        "idx_db_metadata_cache_source",
        "db_metadata_cache",
        ["source_db_type", "source_db_host"],
    )
    op.create_index(
        "idx_db_metadata_cache_collected_at",
        "db_metadata_cache",
        ["collected_at"],
    )

    op.create_table(
        "ai_analysis_result",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("slow_query_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=False, server_default=sa.text("'openai'")),
        sa.Column("model", sa.String(length=100), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("root_cause", sa.Text(), nullable=False),
        sa.Column("recommendations", postgresql.JSONB, nullable=False),
        sa.Column("improvement_level", sa.String(length=10), nullable=True),
        sa.Column("estimated_speedup", sa.String(length=50), nullable=True),
        sa.Column("confidence_score", sa.Numeric(3, 2), nullable=True),
        sa.Column("prompt_metadata", postgresql.JSONB, nullable=True),
        sa.Column("provider_response", postgresql.JSONB, nullable=True),
        sa.Column("analyzed_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.ForeignKeyConstraint(
            ["slow_query_id"],
            ["slow_queries_raw.id"],
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "idx_ai_analysis_query_id",
        "ai_analysis_result",
        ["slow_query_id"],
    )
    op.create_index(
        "idx_ai_analysis_improvement",
        "ai_analysis_result",
        ["improvement_level"],
    )
    op.create_index(
        "idx_ai_analysis_analyzed_at",
        "ai_analysis_result",
        ["analyzed_at"],
    )

    op.add_column(
        "slow_queries_raw",
        sa.Column("ai_analysis_id", postgresql.UUID(as_uuid=True), nullable=True, unique=True),
    )
    op.create_foreign_key(
        "fk_slow_query_ai_analysis",
        "slow_queries_raw",
        "ai_analysis_result",
        ["ai_analysis_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade():  # noqa: D401
    """Rollback AI analysis support structures."""
    op.drop_constraint("fk_slow_query_ai_analysis", "slow_queries_raw", type_="foreignkey")
    op.drop_column("slow_queries_raw", "ai_analysis_id")

    op.drop_index("idx_ai_analysis_analyzed_at", table_name="ai_analysis_result")
    op.drop_index("idx_ai_analysis_improvement", table_name="ai_analysis_result")
    op.drop_index("idx_ai_analysis_query_id", table_name="ai_analysis_result")
    op.drop_table("ai_analysis_result")

    op.drop_index("idx_db_metadata_cache_collected_at", table_name="db_metadata_cache")
    op.drop_index("idx_db_metadata_cache_source", table_name="db_metadata_cache")
    op.drop_table("db_metadata_cache")
