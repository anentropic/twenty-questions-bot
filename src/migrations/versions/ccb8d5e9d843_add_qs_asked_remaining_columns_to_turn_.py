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
    if not column_exists("turn", "questions_asked"):
        op.add_column("turn", sa.Column("questions_asked", sa.Integer(), nullable=True))
    if not column_exists("turn", "questions_remaining"):
        op.add_column(
            "turn", sa.Column("questions_remaining", sa.Integer(), nullable=True)
        )
    op.execute(
        """
        UPDATE turn
        SET
            questions_asked = log.questions_asked,
            questions_remaining = log.questions_remaining
        FROM (
            SELECT
                turn_id,
                "value" -> '$.questions_asked' AS questions_asked,
                "value" -> '$.questions_remaining' AS questions_remaining
            FROM turnlog
            WHERE key = 'BEGIN_TURN'
        ) AS log
        WHERE turn.id = log.turn_id
        """
    )


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("turn", "questions_remaining")
    op.drop_column("turn", "questions_asked")
    # ### end Alembic commands ###
