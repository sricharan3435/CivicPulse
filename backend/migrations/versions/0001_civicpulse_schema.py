"""Create CivicPulse report storage and upgrade existing issue table."""
from secrets import token_urlsafe

from alembic import op
import sqlalchemy as sa

revision = "0001_civicpulse"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("issues"):
        op.create_table(
            "issues",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("title", sa.String(120), nullable=False),
            sa.Column("description", sa.Text(), nullable=False),
            sa.Column("category", sa.String(50), nullable=False),
            sa.Column("latitude", sa.Float(), nullable=False),
            sa.Column("longitude", sa.Float(), nullable=False),
            sa.Column("status", sa.String(30), server_default="pending", nullable=False),
            sa.Column("tracking_code", sa.String(24), nullable=False),
            sa.Column("image_url", sa.String(500), nullable=True),
            sa.Column("verified", sa.Boolean(), server_default=sa.false(), nullable=False),
            sa.Column("assigned_team", sa.String(100), nullable=True),
            sa.Column("priority_score", sa.Float(), server_default="0", nullable=False),
            sa.Column("duplicate_of_id", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
        op.create_index("ix_issues_id", "issues", ["id"])
        op.create_index("ix_issues_category", "issues", ["category"])
        op.create_index("ix_issues_status", "issues", ["status"])
        op.create_index("ix_issues_created_at", "issues", ["created_at"])
    else:
        existing = {column["name"] for column in inspector.get_columns("issues")}
        additions = [
            sa.Column("tracking_code", sa.String(24), nullable=True),
            sa.Column("image_url", sa.String(500), nullable=True),
            sa.Column("verified", sa.Boolean(), server_default=sa.false(), nullable=False),
            sa.Column("assigned_team", sa.String(100), nullable=True),
            sa.Column("priority_score", sa.Float(), server_default="0", nullable=False),
            sa.Column("duplicate_of_id", sa.Integer(), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        ]
        for column in additions:
            if column.name not in existing:
                op.add_column("issues", column)
        rows = bind.execute(sa.text("SELECT id FROM issues WHERE tracking_code IS NULL")).fetchall()
        for (issue_id,) in rows:
            bind.execute(sa.text("UPDATE issues SET tracking_code = :code WHERE id = :id"), {"code": token_urlsafe(12), "id": issue_id})
        with op.batch_alter_table("issues") as batch:
            batch.alter_column("tracking_code", existing_type=sa.String(24), nullable=False)

    index_names = {index["name"] for index in sa.inspect(bind).get_indexes("issues")}
    if "ix_issues_tracking_code" not in index_names:
        op.create_index("ix_issues_tracking_code", "issues", ["tracking_code"], unique=True)


def downgrade():
    op.drop_index("ix_issues_tracking_code", table_name="issues")
    with op.batch_alter_table("issues") as batch:
        for name in ("tracking_code", "image_url", "verified", "assigned_team", "priority_score", "duplicate_of_id", "updated_at"):
            batch.drop_column(name)
