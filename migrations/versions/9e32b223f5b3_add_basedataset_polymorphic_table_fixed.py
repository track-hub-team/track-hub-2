"""Add BaseDataset polymorphic table

Revision ID: b83a68d62254
Revises: 5c1955af8e91
Create Date: 2025-01-XX XX:XX:XX.XXXXXX

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '9e32b223f5b3' 
down_revision = '5c1955af8e91'  
branch_labels = None
depends_on = None


def upgrade():
    # 1. Create base_dataset table
    op.create_table('base_dataset',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('dataset_type', sa.String(length=50), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # 2. Migrate existing data_set records to base_dataset
    connection = op.get_bind()
    
    # Get existing datasets
    result = connection.execute(sa.text("""
        SELECT id, user_id, created_at FROM data_set
    """))
    
    existing_datasets = result.fetchall()
    
    # Insert into base_dataset
    for dataset in existing_datasets:
        connection.execute(sa.text("""
            INSERT INTO base_dataset (id, dataset_type, user_id, created_at)
            VALUES (:id, 'uvl', :user_id, :created_at)
        """), {
            'id': dataset[0],
            'user_id': dataset[1],
            'created_at': dataset[2]
        })
    
    # 3. Drop foreign key constraint FIRST (this is the fix!)
    op.drop_constraint('data_set_ibfk_1', 'data_set', type_='foreignkey')
    
    # 4. NOW drop the columns
    op.drop_column('data_set', 'created_at')
    op.drop_column('data_set', 'user_id')
    
    # 5. Add foreign key to base_dataset
    op.create_foreign_key(
        'data_set_base_fk',
        'data_set', 'base_dataset',
        ['id'], ['id']
    )


def downgrade():
    # 1. Drop foreign key to base_dataset
    op.drop_constraint('data_set_base_fk', 'data_set', type_='foreignkey')
    
    # 2. Re-add columns to data_set
    op.add_column('data_set', sa.Column('user_id', sa.Integer(), nullable=True))
    op.add_column('data_set', sa.Column('created_at', sa.DateTime(), nullable=True))
    
    # 3. Copy data back from base_dataset
    connection = op.get_bind()
    connection.execute(sa.text("""
        UPDATE data_set ds
        INNER JOIN base_dataset bd ON ds.id = bd.id
        SET ds.user_id = bd.user_id,
            ds.created_at = bd.created_at
    """))
    
    # 4. Make columns NOT NULL
    op.alter_column('data_set', 'user_id', nullable=False)
    op.alter_column('data_set', 'created_at', nullable=False)
    
    # 5. Re-create foreign key
    op.create_foreign_key(
        'data_set_ibfk_1',
        'data_set', 'user',
        ['user_id'], ['id']
    )
    
    # 6. Drop base_dataset table
    op.drop_table('base_dataset')