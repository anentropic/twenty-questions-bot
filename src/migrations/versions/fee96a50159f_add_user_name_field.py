"""add user.name field

Revision ID: fee96a50159f
Revises: f56e092a754c
Create Date: 2023-05-20 18:42:10.732619

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision = "fee96a50159f"
down_revision = "f56e092a754c"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("user") as batch_op:
        batch_op.add_column(
            sa.Column(
                "name",
                sqlmodel.sql.sqltypes.AutoString(),
                nullable=True,
            ),
        )
        batch_op.execute(
            "UPDATE user SET name = upper(substr( username, 1, 1 )) || substr( username, 2 )"
        )
        batch_op.alter_column(
            "name",
            nullable=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("user") as batch_op:
        batch_op.drop_column("name")
