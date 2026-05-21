"""alter storage_locations: add region/cost_per_bag_per_month/is_active/last_verified_date, drop cost_per_bag, add wfp_prices FK

Bootstrap paths
---------------
New environment:
  1. Start the app once — Base.metadata.create_all() in app/main.py creates all
     tables with the current schema and stamps this revision via
     alembic.command.stamp(...) (see app/main.py startup logic).
  2. Future schema changes: alembic upgrade head.

Existing environment (pre-migration schema, has cost_per_bag but not the new columns):
  alembic upgrade head — all ops below are guarded and safe to run either way.

Revision ID: 1c7341e28d12
Revises:
Create Date: 2026-05-20 21:16:21.648941

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = '1c7341e28d12'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _col_exists(table: str, col: str) -> bool:
    insp = sa_inspect(op.get_bind())
    if not insp.has_table(table):
        return False
    return col in [c['name'] for c in insp.get_columns(table)]


def _find_fk(table: str, constrained_cols: list, referred_table: str) -> str | None:
    """Return the constraint name of a matching FK, or None if not found.
    Matches by columns so auto-generated names (common on MySQL) are handled correctly."""
    insp = sa_inspect(op.get_bind())
    if not insp.has_table(table):
        return None
    for fk in insp.get_foreign_keys(table):
        if fk['constrained_columns'] == constrained_cols and fk['referred_table'] == referred_table:
            return fk['name']
    return None


def upgrade() -> None:
    # language_admin1 and language_admin2 are intentionally unmanaged by Alembic
    # (no ORM model — loaded via load_data.py with if_exists='replace').
    insp = sa_inspect(op.get_bind())

    # storage_locations column changes — guarded independently of the FK below.
    if insp.has_table('storage_locations'):
        if not _col_exists('storage_locations', 'region'):
            op.add_column('storage_locations', sa.Column('region', sa.String(length=100), nullable=True))
        if not _col_exists('storage_locations', 'cost_per_bag_per_month'):
            op.add_column('storage_locations', sa.Column('cost_per_bag_per_month', sa.Float(), nullable=True))
        # Migrate existing cost_per_bag values before dropping the column.
        # The old column held a per-bag monthly rate so the values carry over directly.
        if _col_exists('storage_locations', 'cost_per_bag'):
            op.execute(sa.text(
                "UPDATE storage_locations "
                "SET cost_per_bag_per_month = cost_per_bag "
                "WHERE cost_per_bag_per_month IS NULL AND cost_per_bag IS NOT NULL"
            ))
            op.drop_column('storage_locations', 'cost_per_bag')
        if not _col_exists('storage_locations', 'is_active'):
            op.add_column('storage_locations', sa.Column('is_active', sa.Boolean(), nullable=True, server_default=sa.true()))
            op.execute(sa.text("UPDATE storage_locations SET is_active = TRUE WHERE is_active IS NULL"))
            op.alter_column('storage_locations', 'is_active', existing_type=sa.Boolean(), nullable=False)
        if not _col_exists('storage_locations', 'last_verified_date'):
            op.add_column('storage_locations', sa.Column('last_verified_date', sa.DateTime(), nullable=True))

    # wfp_prices FK — guarded separately; unrelated to storage_locations.
    if insp.has_table('wfp_prices') and insp.has_table('wfp_markets'):
        if _find_fk('wfp_prices', ['market_id'], 'wfp_markets') is None:
            op.create_foreign_key('fk_wfp_prices_market_id_wfp_markets', 'wfp_prices', 'wfp_markets', ['market_id'], ['market_id'])


def downgrade() -> None:
    insp = sa_inspect(op.get_bind())

    # wfp_prices FK — guarded separately; unrelated to storage_locations.
    if insp.has_table('wfp_prices') and insp.has_table('wfp_markets'):
        fk_name = _find_fk('wfp_prices', ['market_id'], 'wfp_markets')
        if fk_name:
            op.drop_constraint(fk_name, 'wfp_prices', type_='foreignkey')

    # storage_locations column changes — guarded independently.
    if insp.has_table('storage_locations'):
        if not _col_exists('storage_locations', 'cost_per_bag'):
            op.add_column('storage_locations', sa.Column('cost_per_bag', mysql.FLOAT(), nullable=True))
        # Restore cost_per_bag values from cost_per_bag_per_month before dropping the new column.
        if _col_exists('storage_locations', 'cost_per_bag_per_month'):
            op.execute(sa.text(
                "UPDATE storage_locations "
                "SET cost_per_bag = cost_per_bag_per_month "
                "WHERE cost_per_bag IS NULL AND cost_per_bag_per_month IS NOT NULL"
            ))
            op.drop_column('storage_locations', 'cost_per_bag_per_month')
        if _col_exists('storage_locations', 'last_verified_date'):
            op.drop_column('storage_locations', 'last_verified_date')
        if _col_exists('storage_locations', 'is_active'):
            op.alter_column('storage_locations', 'is_active', existing_type=sa.Boolean(), nullable=True)
            op.drop_column('storage_locations', 'is_active')
        if _col_exists('storage_locations', 'region'):
            op.drop_column('storage_locations', 'region')
