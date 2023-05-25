"""rename turn.game_id field

Revision ID: cc17c70b259a
Revises: 
Create Date: 2023-05-18 19:38:28.163292

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = "cc17c70b259a"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("turn") as batch_op:
        batch_op.drop_index("turn_game_id")
        batch_op.alter_column("game_id", new_column_name="gamesession_id")
        batch_op.create_index("turn_gamesession_id", ["gamesession_id"])


def downgrade() -> None:
    with op.batch_alter_table("turn") as batch_op:
        batch_op.drop_index("turn_gamesession_id")
        batch_op.alter_column("gamesession_id", new_column_name="game_id")
        batch_op.create_index("turn_game_id", ["game_id"])
