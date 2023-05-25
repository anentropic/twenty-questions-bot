"""add qs asked/remaining columns to turn table

Revision ID: ccb8d5e9d843
Revises: fee96a50159f
Create Date: 2023-05-22 11:02:22.586308

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "ccb8d5e9d843"
down_revision = "fee96a50159f"
branch_labels = None
depends_on = None


def column_exists(table_name, column_name):
    bind = op.get_context().bind
    insp = sa.inspect(bind)
    columns = insp.get_columns(table_name)
    return any(c["name"] == column_name for c in columns)


def upgrade() -> None:
    with op.batch_alter_table("turn") as batch_op:
        batch_op.add_column(sa.Column("questions_asked", sa.Integer(), nullable=True))
        batch_op.add_column(
            sa.Column("questions_remaining", sa.Integer(), nullable=True)
        )
        batch_op.execute(
            """
            UPDATE turn
            SET
                questions_asked = log.questions_asked,
                questions_remaining = log.questions_remaining
            FROM (
                SELECT
                    turn_id,
                    json_extract("value", '$.questions_asked') AS questions_asked,
                    json_extract("value", '$.questions_remaining') AS questions_remaining
                FROM turnlog
                WHERE key = 'BEGIN_TURN'
            ) AS log
            WHERE turn.id = log.turn_id
            """
        )


def downgrade() -> None:
    with op.batch_alter_table("turn") as batch_op:
        batch_op.drop_column("questions_remaining")
        batch_op.drop_column("questions_asked")
