# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Create the Cloud Credential table.

Revision ID: 011
Revises: table template

"""

# revision identifiers, used by Alembic.
revision = '011'
down_revision = '010'

from alembic import op
import sqlalchemy as sa


MYSQL_ENGINE = 'InnoDB'
MYSQL_CHARSET = 'utf8'


def upgrade():
    """It creates the table cloud credentials.
    """

    op.create_table(
        'cloud_credentials',
        sa.Column('created', sa.DateTime(), nullable=False),
        sa.Column('updated', sa.DateTime(), nullable=False),
        sa.Column('id', sa.String(length=255), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('version', sa.BigInteger(), nullable=False),
        sa.Column('tenant_id', sa.String(length=36), nullable=False),
        sa.Column('cloud_type',sa.String(36), nullable=False),
        sa.Column('user',sa.String(36), nullable=False),
        sa.Column('key', sa.Text(), nullable=True),
        sa.Column('private_key', sa.Text(), nullable=True),
        sa.Column('endpoint', sa.Text(), nullable=True),
        sa.Column('options', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tenant_id', 'name'),
        mysql_engine=MYSQL_ENGINE,
        mysql_charset=MYSQL_CHARSET
    )

    op.create_table(
        'instance_credentials',
        sa.Column('created', sa.DateTime(), nullable=False),
        sa.Column('updated', sa.DateTime(), nullable=False),
        sa.Column('id', sa.String(length=255), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('version', sa.BigInteger(), nullable=False),
        sa.Column('tenant_id', sa.String(length=36), nullable=False),
        sa.Column('cloud_type',sa.String(36), nullable=False),
        sa.Column('user',sa.String(36), nullable=False),
        sa.Column('password', sa.Text(), nullable=True),
        sa.Column('private_key', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tenant_id', 'name'),
        mysql_engine=MYSQL_ENGINE,
        mysql_charset=MYSQL_CHARSET
    )


def downgrade():
    op.drop_table('cloud_credentials')
    op.drop_table('instance_credentials')
