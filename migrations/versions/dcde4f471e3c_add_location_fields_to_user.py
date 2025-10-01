"""Add location fields to User

Revision ID: dcde4f471e3c
Revises: 30cc30d9cb4d
Create Date: 2025-10-01 14:54:48.772296

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'dcde4f471e3c'
down_revision = '30cc30d9cb4d'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.add_column(sa.Column('city', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('state', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('country', sa.String(length=100), nullable=True))


def downgrade():
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.drop_column('country')
        batch_op.drop_column('state')
        batch_op.drop_column('city')
