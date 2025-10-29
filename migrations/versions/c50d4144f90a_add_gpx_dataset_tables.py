"""Add GPX dataset tables

Revision ID: XXXXX
Revises: (el ID de la migración anterior)
Create Date: 2025-XX-XX XX:XX:XX.XXXXXX

"""
from alembic import op
import sqlalchemy as sa

revision = 'c50d4144f90a' 
down_revision = '9e32b223f5b3' 
branch_labels = None
depends_on = None


def upgrade():
    # 1. Create gpx_meta_data
    op.create_table('gpx_meta_data',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('hikr_id', sa.String(length=50), nullable=True),
        sa.Column('hikr_user', sa.String(length=100), nullable=True),
        sa.Column('hikr_url', sa.String(length=500), nullable=True),
        sa.Column('length_2d', sa.Float(), nullable=True),
        sa.Column('length_3d', sa.Float(), nullable=True),
        sa.Column('max_elevation', sa.Float(), nullable=True),
        sa.Column('min_elevation', sa.Float(), nullable=True),
        sa.Column('uphill', sa.Float(), nullable=True),
        sa.Column('downhill', sa.Float(), nullable=True),
        sa.Column('start_time', sa.DateTime(), nullable=True),
        sa.Column('end_time', sa.DateTime(), nullable=True),
        sa.Column('moving_time', sa.Float(), nullable=True),
        sa.Column('max_speed', sa.Float(), nullable=True),
        sa.Column('difficulty', sa.Enum('T1', 'T2', 'T3', 'T4', 'T5', 'T6', name='gpxdifficultyrating'), nullable=True),
        sa.Column('bounds_min_lat', sa.Float(), nullable=True),
        sa.Column('bounds_max_lat', sa.Float(), nullable=True),
        sa.Column('bounds_min_lon', sa.Float(), nullable=True),
        sa.Column('bounds_max_lon', sa.Float(), nullable=True),
        sa.Column('gpx_content', sa.Text(), nullable=True),
        sa.Column('tags', sa.String(length=200), nullable=True),
        sa.Column('publication_doi', sa.String(length=120), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_gpx_meta_data_hikr_id'), 'gpx_meta_data', ['hikr_id'], unique=True)
    
    # 2. Create gpx_dataset
    op.create_table('gpx_dataset',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('gpx_meta_data_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['gpx_meta_data_id'], ['gpx_meta_data.id'], ),
        sa.ForeignKeyConstraint(['id'], ['base_dataset.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # 3. Add gpx_meta_data_id to author
    op.add_column('author', sa.Column('gpx_meta_data_id', sa.Integer(), nullable=True))
    op.create_foreign_key('author_gpx_fk', 'author', 'gpx_meta_data', ['gpx_meta_data_id'], ['id'])


def downgrade():
    op.drop_constraint('author_gpx_fk', 'author', type_='foreignkey')
    op.drop_column('author', 'gpx_meta_data_id')
    op.drop_table('gpx_dataset')
    op.drop_index(op.f('ix_gpx_meta_data_hikr_id'), table_name='gpx_meta_data')
    op.drop_table('gpx_meta_data')