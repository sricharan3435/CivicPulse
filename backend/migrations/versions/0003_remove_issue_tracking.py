"""Remove private tracking codes; submitted status remains visible in the app."""
from secrets import token_urlsafe

from alembic import op
import sqlalchemy as sa

revision = "0003_remove_issue_tracking"
down_revision = "0002_user_accounts"
branch_labels = None
depends_on = None


def upgrade():
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("issues"):
        return
    indexes = {index["name"] for index in inspector.get_indexes("issues")}
    if "ix_issues_tracking_code" in indexes:
        op.drop_index("ix_issues_tracking_code", table_name="issues")
    columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("issues")}
    if "tracking_code" in columns:
        op.drop_column("issues", "tracking_code")


def downgrade():
    op.add_column("issues", sa.Column("tracking_code", sa.String(24), nullable=True))
    bind = op.get_bind()
    rows = bind.execute(sa.text("SELECT id FROM issues WHERE tracking_code IS NULL")).fetchall()
    for (issue_id,) in rows:
        bind.execute(sa.text("UPDATE issues SET tracking_code = :code WHERE id = :id"), {"code": token_urlsafe(12), "id": issue_id})
    with op.batch_alter_table("issues") as batch:
        batch.alter_column("tracking_code", existing_type=sa.String(24), nullable=False)
    op.create_index("ix_issues_tracking_code", "issues", ["tracking_code"], unique=True)
