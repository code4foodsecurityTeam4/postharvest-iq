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
    return col in [c['name'] for c in sa_inspect(op.get_bind()).get_columns(table)]


def _fk_exists(table: str, name: str) -> bool:
    return name in [fk['name'] for fk in sa_inspect(op.get_bind()).get_foreign_keys(table)]


def upgrade() -> None:
    # language_admin1 and language_admin2 are intentionally unmanaged by Alembic
    # (no ORM model — loaded via load_data.py with if_exists='replace').
    if not _col_exists('storage_locations', 'region'):
        op.add_column('storage_locations', sa.Column('region', sa.String(length=100), nullable=True))
    if not _col_exists('storage_locations', 'cost_per_bag_per_month'):
        op.add_column('storage_locations', sa.Column('cost_per_bag_per_month', sa.Float(), nullable=True))
    if not _col_exists('storage_locations', 'is_active'):
        op.add_column('storage_locations', sa.Column('is_active', sa.Boolean(), nullable=True, server_default=sa.true()))
        op.execute(sa.text("UPDATE storage_locations SET is_active = TRUE WHERE is_active IS NULL"))
        op.alter_column('storage_locations', 'is_active', existing_type=sa.Boolean(), nullable=False)
    if not _col_exists('storage_locations', 'last_verified_date'):
        op.add_column('storage_locations', sa.Column('last_verified_date', sa.DateTime(), nullable=True))
    if _col_exists('storage_locations', 'cost_per_bag'):
        op.drop_column('storage_locations', 'cost_per_bag')
    if not _fk_exists('wfp_prices', 'fk_wfp_prices_market_id_wfp_markets'):
        op.create_foreign_key('fk_wfp_prices_market_id_wfp_markets', 'wfp_prices', 'wfp_markets', ['market_id'], ['market_id'])


def downgrade() -> None:
    if _fk_exists('wfp_prices', 'fk_wfp_prices_market_id_wfp_markets'):
        op.drop_constraint('fk_wfp_prices_market_id_wfp_markets', 'wfp_prices', type_='foreignkey')
    if not _col_exists('storage_locations', 'cost_per_bag'):
        op.add_column('storage_locations', sa.Column('cost_per_bag', mysql.FLOAT(), nullable=True))
    if _col_exists('storage_locations', 'last_verified_date'):
        op.drop_column('storage_locations', 'last_verified_date')
    if _col_exists('storage_locations', 'is_active'):
        op.alter_column('storage_locations', 'is_active', existing_type=sa.Boolean(), nullable=True)
        op.drop_column('storage_locations', 'is_active')
    if _col_exists('storage_locations', 'cost_per_bag_per_month'):
        op.drop_column('storage_locations', 'cost_per_bag_per_month')
    if _col_exists('storage_locations', 'region'):
        op.drop_column('storage_locations', 'region')
