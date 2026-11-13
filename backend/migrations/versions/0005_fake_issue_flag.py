"""Let administrators flag and restore fake reports."""
from alembic import op
import sqlalchemy as sa

revision = "0005_fake_issue_flag"
down_revision = "0004_user_roles"
branch_labels = None
depends_on = None


def upgrade():
    columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("issues")}
    if "is_fake" not in columns:
        op.add_column("issues", sa.Column("is_fake", sa.Boolean(), server_default=sa.false(), nullable=False))


def downgrade():
    columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("issues")}
    if "is_fake" in columns:
        op.drop_column("issues", "is_fake")
