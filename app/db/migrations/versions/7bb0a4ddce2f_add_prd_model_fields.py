"""add_prd_model_fields

Revision ID: 7bb0a4ddce2f
Revises: 4df782f0fdba
Create Date: 2026-08-29 23:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "7bb0a4ddce2f"
down_revision: Union[str, None] = "4df782f0fdba"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("standards", sa.Column("revision", sa.String(), nullable=True))
    op.add_column("standards", sa.Column("related_standards", sa.JSON(), nullable=True))
    op.add_column("qcos", sa.Column("amendment_date", sa.Date(), nullable=True))


def downgrade() -> None:
    op.drop_column("qcos", "amendment_date")
    op.drop_column("standards", "related_standards")
    op.drop_column("standards", "revision")
