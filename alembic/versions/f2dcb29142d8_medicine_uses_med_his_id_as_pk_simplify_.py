"""medicine uses med_his_id as PK; simplify prescription_detail

Revision ID: f2dcb29142d8
Revises: 7126b0accac1
Create Date: 2026-09-15 21:34:58.906306

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f2dcb29142d8'
down_revision: Union[str, Sequence[str], None] = '7126b0accac1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Drop FKs pointing at medicine.id first -- medicine_pkey can't be dropped while they exist.
    op.drop_constraint('tray_medicine_id_fkey', 'tray', type_='foreignkey')
    op.drop_constraint('prescription_detail_medicine_id_fkey', 'prescription_detail', type_='foreignkey')

    # --- medicine: replace surrogate id + med_code with a single med_his_id PK ---
    op.add_column('medicine', sa.Column('med_his_id', sa.String(), nullable=False))
    op.drop_constraint('uq_medicine_med_code', 'medicine', type_='unique')
    op.drop_constraint('medicine_pkey', 'medicine', type_='primary')
    op.drop_column('medicine', 'id')
    op.drop_column('medicine', 'med_code')
    op.drop_column('medicine', 'specs')
    op.drop_column('medicine', 'factory_name')
    op.drop_column('medicine', 'unit')
    op.create_primary_key('medicine_pkey', 'medicine', ['med_his_id'])

    # --- tray: medicine_id (int FK -> medicine.id) becomes med_his_id (str FK -> medicine.med_his_id) ---
    op.add_column('tray', sa.Column('med_his_id', sa.String(), nullable=True))
    op.create_foreign_key('tray_med_his_id_fkey', 'tray', 'medicine', ['med_his_id'], ['med_his_id'])
    op.drop_column('tray', 'medicine_id')

    # --- prescription_detail: drop medicine_id + all snapshot columns, keep med_his_id only ---
    op.alter_column('prescription_detail', 'med_his_id', existing_type=sa.String(), nullable=False)
    op.drop_column('prescription_detail', 'med_factory_name')
    op.drop_column('prescription_detail', 'med_name')
    op.drop_column('prescription_detail', 'med_unit')
    op.drop_column('prescription_detail', 'med_hint')
    op.drop_column('prescription_detail', 'medicine_id')
    op.drop_column('prescription_detail', 'med_specs')


def downgrade() -> None:
    """Downgrade schema."""
    # --- prescription_detail: restore snapshot columns + medicine_id FK ---
    op.add_column('prescription_detail', sa.Column('med_specs', sa.String(), nullable=True))
    op.add_column('prescription_detail', sa.Column('medicine_id', sa.Integer(), nullable=True))
    op.add_column('prescription_detail', sa.Column('med_hint', sa.String(), nullable=True))
    op.add_column('prescription_detail', sa.Column('med_unit', sa.String(), nullable=True))
    op.add_column('prescription_detail', sa.Column('med_name', sa.String(), nullable=False, server_default=''))
    op.alter_column('prescription_detail', 'med_name', server_default=None)
    op.add_column('prescription_detail', sa.Column('med_factory_name', sa.String(), nullable=True))
    op.alter_column('prescription_detail', 'med_his_id', existing_type=sa.String(), nullable=True)

    # --- tray: drop med_his_id FK/column, restore medicine_id ---
    op.drop_constraint('tray_med_his_id_fkey', 'tray', type_='foreignkey')
    op.add_column('tray', sa.Column('medicine_id', sa.Integer(), nullable=True))
    op.drop_column('tray', 'med_his_id')

    # --- medicine: restore surrogate id PK + med_code + dropped columns ---
    op.drop_constraint('medicine_pkey', 'medicine', type_='primary')
    op.execute('ALTER TABLE medicine ADD COLUMN id SERIAL')
    op.create_primary_key('medicine_pkey', 'medicine', ['id'])
    op.add_column('medicine', sa.Column('med_code', sa.String(), nullable=False, server_default=''))
    op.alter_column('medicine', 'med_code', server_default=None)
    op.create_unique_constraint('uq_medicine_med_code', 'medicine', ['med_code'])
    op.add_column('medicine', sa.Column('specs', sa.String(), nullable=True))
    op.add_column('medicine', sa.Column('factory_name', sa.String(), nullable=True))
    op.add_column('medicine', sa.Column('unit', sa.String(), nullable=True))
    op.drop_column('medicine', 'med_his_id')

    # --- recreate FKs to medicine.id now that it exists again ---
    op.create_foreign_key('tray_medicine_id_fkey', 'tray', 'medicine', ['medicine_id'], ['id'])
    op.create_foreign_key(
        'prescription_detail_medicine_id_fkey', 'prescription_detail', 'medicine', ['medicine_id'], ['id']
    )
