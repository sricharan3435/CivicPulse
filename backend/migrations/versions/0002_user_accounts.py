"""Add citizen accounts, persistent sessions, and report ownership."""
from alembic import op
import sqlalchemy as sa

revision = "0002_user_accounts"
down_revision = "0001_civicpulse"
branch_labels = None
depends_on = None


def _indexes(table_name):
    return {index["name"] for index in sa.inspect(op.get_bind()).get_indexes(table_name)}


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("users"):
        op.create_table(
            "users",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("full_name", sa.String(100), nullable=False),
            sa.Column("email", sa.String(254), nullable=False),
            sa.Column("password_hash", sa.String(255), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
        op.create_index("ix_users_id", "users", ["id"])
        op.create_index("ix_users_email", "users", ["email"], unique=True)

    if not sa.inspect(bind).has_table("user_sessions"):
        op.create_table(
            "user_sessions",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("token_hash", sa.String(64), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
    for name, column in (
        ("ix_user_sessions_user_id", "user_id"),
        ("ix_user_sessions_token_hash", "token_hash"),
        ("ix_user_sessions_expires_at", "expires_at"),
    ):
        if name not in _indexes("user_sessions"):
            op.create_index(name, "user_sessions", [column], unique=(column == "token_hash"))

    issue_columns = {column["name"] for column in sa.inspect(bind).get_columns("issues")}
    if "reporter_id" not in issue_columns:
        op.add_column("issues", sa.Column("reporter_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True))
    if "ix_issues_reporter_id" not in _indexes("issues"):
        op.create_index("ix_issues_reporter_id", "issues", ["reporter_id"])


def downgrade():
    op.drop_index("ix_issues_reporter_id", table_name="issues")
    op.drop_column("issues", "reporter_id")
    op.drop_index("ix_user_sessions_expires_at", table_name="user_sessions")
    op.drop_index("ix_user_sessions_token_hash", table_name="user_sessions")
    op.drop_index("ix_user_sessions_user_id", table_name="user_sessions")
    op.drop_table("user_sessions")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_index("ix_users_id", table_name="users")
    op.drop_table("users")
