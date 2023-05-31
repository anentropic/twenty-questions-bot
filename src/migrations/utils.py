from alembic import op
import sqlalchemy as sa


def index_exists(table_name, index_name):
    bind = op.get_context().bind
    insp = sa.inspect(bind)
    indexes = insp.get_indexes(table_name)
    return any(i["name"] == index_name for i in indexes)


def column_exists(table_name, column_name):
    bind = op.get_context().bind
    insp = sa.inspect(bind)
    columns = insp.get_columns(table_name)
    return any(c["name"] == column_name for c in columns)
