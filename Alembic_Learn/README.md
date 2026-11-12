# Alembic
A tool to manage your sql databsem, using sqlalchemy engine. It usages Migration Scripts to maintain database.

## Installation
```bash
pip install alembic
```

## Creating Alembic Environment
```bash
cd /path/to/yourproject
source /path/to/yourproject/.venv/bin/activate   # assuming a local virtualenv
alembic init alembic
```

## Structure of Alembic Directory
```
yourproject/
    alembic/
        env.py
        README
        script.py.mako
        versions/
            3512b954651e_add_account.py
            2b1ae634e5cd_add_order_id.py
            3adcc9a56557_rename_username_field.py
```

- yourproject - this is the root of your application’s source code, or some directory within it.

- alembic - this directory lives within your application’s source tree and is the home of the migration environment. It can be named anything, and a project that uses multiple databases may even have more than one.

- env.py - This is a Python script that is run whenever the alembic migration tool is invoked. At the very least, it contains instructions to configure and generate a SQLAlchemy engine, procure a connection from that engine along with a transaction, and then invoke the migration engine, using the connection as a source of database connectivity.

- The env.py script is part of the generated environment so that the way migrations run is entirely customizable. The exact specifics of how to connect are here, as well as the specifics of how the migration environment are invoked. The script can be modified so that multiple engines can be operated upon, custom arguments can be passed into the migration environment, application-specific libraries and models can be loaded in and made available.

- Alembic includes a set of initialization templates which feature different varieties of env.py for different use cases.

- README - included with the various environment templates, should have something informative.

- script.py.mako - This is a Mako template file which is used to generate new migration scripts. Whatever is here is used to generate new files within versions/. This is scriptable so that the structure of each migration file can be controlled, including standard imports to be within each, as well as changes to the structure of the upgrade() and downgrade() functions. For example, the multidb environment allows for multiple functions to be generated using a naming scheme upgrade_engine1(), upgrade_engine2().

- versions/ - This directory holds the individual version scripts. Users of other migration tools may notice that the files here don’t use ascending integers, and instead use a partial GUID approach. In Alembic, the ordering of version scripts is relative to directives within the scripts themselves, and it is theoretically possible to “splice” version files in between others, allowing migration sequences from different branches to be merged, albeit carefully by hand.


## Creating a Migration Script

### Generating Revisions

```bash
$ alembic revision -m "create account table"
Generating /path/to/yourproject/alembic/versions/1975ea83b712_create_accoun
t_table.py...done
```

Generated file will look like
```python
"""create account table

Revision ID: 1975ea83b712
Revises:
Create Date: 2011-11-08 11:40:27.089406

"""

# revision identifiers, used by Alembic.
revision = '1975ea83b712'
down_revision = None
branch_labels = None

from alembic import op
import sqlalchemy as sa

def upgrade():
    pass

def downgrade():
    pass
```

The file contains some header information, identifiers for the current revision and a “downgrade” revision, an import of basic Alembic directives, and empty upgrade() and downgrade() functions. 

Our job here is to populate the upgrade() and downgrade() functions with directives that will apply a set of changes to our database. Typically, upgrade() is required while downgrade() is only needed if down-revision capability is desired, though it’s probably a good idea.

### Adding our DB change instructions

```python
def upgrade():
    op.create_table(
        'account',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('name', sa.String(50), nullable=False),
        sa.Column('description', sa.Unicode(200)),
    )

def downgrade():
    op.drop_table('account')
```

### Running Our Migration

```bash
$ alembic upgrade head
INFO  [alembic.context] Context class PostgresqlContext.
INFO  [alembic.context] Will assume transactional DDL.
INFO  [alembic.context] Running upgrade None -> 1975ea83b712
```

## Revision Identifier
A 12 Character string that is an identifier for the migration, `1975ea83b712`

## Partial Revision Identifier
Instead of 12 character identifier, we can use starting chars, and alembic will identify the migration, 
```bash
alembic upgrade 1975ea83b712
# or
alembic upgrade 197
# Both are correct
```

## Relative Migration Identifiers
Relative upgrades/downgrades are also supported. To move two versions from the current, a decimal value “+N” can be supplied

```bash
alembic upgrade +2
alembic downgrade -1
```

We can also specify the version from which we want to run migration in relative migration
```bash
alembic upgrade 197+2
alembic downgrade 197-1
```

## Getting Information

### Current Revision
To know the current executed migration, use below one

```bash
alembic current
INFO  [alembic.context] Context class PostgresqlContext.
INFO  [alembic.context] Will assume transactional DDL.
Current revision for postgresql://scott:XXXXX@localhost/test: 1975ea83b712 -> ae1027a6acf (head), Add 
```

### Migration History
You can get the sequence in which migrations are executed, it is like a `doubly linkedlist`, use below command to list the history

```bash
alembic history 

e1188875b382 -> 21bdc430ed05 (head), Add meta to transaction_status table
c00265bd1127 -> e1188875b382, RefundInit
6c6b22e26647 -> c00265bd1127, add cod_prepaid_payment model
452f2a72ec25 -> 6c6b22e26647, UserCODlimit model creation
f43a9fc85469 -> 452f2a72ec25, Add payment mode in refund
ec212199f0a4 -> f43a9fc85469, Models for Payment Link
```

### Migration History with Verbose
```bash
alembic history --verbose

Rev: ae1027a6acf (head)
Parent: 1975ea83b712
Path: /path/to/yourproject/alembic/versions/ae1027a6acf_add_a_column.py

    add a column

    Revision ID: ae1027a6acf
    Revises: 1975ea83b712
    Create Date: 2014-11-20 13:02:54.849677

Rev: 1975ea83b712
Parent: <base>
Path: /path/to/yourproject/alembic/versions/1975ea83b712_add_account_table.py

    create account table

    Revision ID: 1975ea83b712
    Revises:
    Create Date: 2014-11-20 13:02:46.257104
```

## Downgrading
 You can downgrade migration, using below command
 ```bash
 alembic downgrade base
INFO  [alembic.context] Context class PostgresqlContext.
INFO  [alembic.context] Will assume transactional DDL.
INFO  [alembic.context] Running downgrade ae1027a6acf -> 1975ea83b712
INFO  [alembic.context] Running downgrade 1975ea83b712 -> None
```