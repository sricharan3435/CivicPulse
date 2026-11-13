"""Add citizen/admin roles to user accounts."""
from alembic import op
import sqlalchemy as sa

revision = "0004_user_roles"
down_revision = "0003_remove_issue_tracking"
branch_labels = None
depends_on = None


def upgrade():
    columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("users")}
    if "role" not in columns:
        op.add_column("users", sa.Column("role", sa.String(20), server_default="citizen", nullable=False))


def downgrade():
    columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("users")}
    if "role" in columns:
        op.drop_column("users", "role")
