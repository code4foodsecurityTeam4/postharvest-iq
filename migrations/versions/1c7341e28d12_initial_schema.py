"""alter storage_locations: add region/cost/active/verified columns, add wfp_prices FK

Full schema bootstrap happens via Base.metadata.create_all() in app/main.py (startup)
and data/load_data.py (CSV seed). This migration only applies incremental changes
on top of that baseline — running it against a truly empty DB will fail.

Revision ID: 1c7341e28d12
Revises:
Create Date: 2026-05-20 21:16:21.648941

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = '1c7341e28d12'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # language_admin1 and language_admin2 are intentionally unmanaged by Alembic
    # (no ORM model — loaded via load_data.py with if_exists='replace').
    op.add_column('storage_locations', sa.Column('region', sa.String(length=100), nullable=True))
    op.add_column('storage_locations', sa.Column('cost_per_bag_per_month', sa.Float(), nullable=True))
    op.add_column('storage_locations', sa.Column('is_active', sa.Boolean(), nullable=True, server_default=sa.true()))
    op.execute(sa.text("UPDATE storage_locations SET is_active = TRUE WHERE is_active IS NULL"))
    op.alter_column('storage_locations', 'is_active', existing_type=sa.Boolean(), nullable=False)
    op.add_column('storage_locations', sa.Column('last_verified_date', sa.DateTime(), nullable=True))
    op.drop_column('storage_locations', 'cost_per_bag')
    op.create_foreign_key('fk_wfp_prices_market_id_wfp_markets', 'wfp_prices', 'wfp_markets', ['market_id'], ['market_id'])


def downgrade() -> None:
    op.drop_constraint('fk_wfp_prices_market_id_wfp_markets', 'wfp_prices', type_='foreignkey')
    op.add_column('storage_locations', sa.Column('cost_per_bag', mysql.FLOAT(), nullable=True))
    op.drop_column('storage_locations', 'last_verified_date')
    op.alter_column('storage_locations', 'is_active', existing_type=sa.Boolean(), nullable=True)
    op.drop_column('storage_locations', 'is_active')
    op.drop_column('storage_locations', 'cost_per_bag_per_month')
    op.drop_column('storage_locations', 'region')
