"""rename turn.game_id field

Revision ID: cc17c70b259a
Revises: 
Create Date: 2023-05-18 19:38:28.163292

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'cc17c70b259a'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index('turn_game_id', table_name='turn')
    op.alter_column('turn', 'game_id', new_column_name='gamesession_id')
    op.create_index('turn_gamesession_id', 'turn', ['gamesession_id'])
    


def downgrade() -> None:
    op.drop_index('turn_gamesession_id', table_name='turn')
    op.alter_column('turn', 'gamesession_id', new_column_name='game_id')
    op.create_index('turn_game_id', 'turn', ['game_id'])
