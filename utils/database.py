"""This contains useful functions for database related operations"""

import aiosqlite
import os

async def createTable(db_path, table_name, columns_dict):
    """
    Create or update table. Assign default values. If table exists but not a column, add
    the column and assign default value.

    Parameters
    ----------
    db_path : str
        The path of the database. Create if not already exists.
    table_name : str
        The name of the created table.
    columns_dict : dict
        The {column : value} dictionary defining the columns and default values of the table.

    """
    if os.path.exists(db_path) == False:
        open(db_path, "a")
        print(f"Warning [database.createTable]: Database created at {db_path}")

    async with aiosqlite.connect(db_path) as db:
        async with db.cursor() as cursor:
            # Check if table exists
            await cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'")
            table_exists = await cursor.fetchone()

            if not table_exists:
                # Table doesn't exist, create it
                columns_definition = ', '.join(columns_dict.keys())#[f"{col_name} {col_type}" for col_name, col_type in columns_dict.items()])
                create_query = f"CREATE TABLE {table_name} ({columns_definition})"
                await cursor.execute(create_query)
                await db.commit()

            # Check if columns exist
            await cursor.execute(f"PRAGMA table_info({table_name})")
            existing_columns = await cursor.fetchall()
            existing_column_names = [column[1] for column in existing_columns]

            # Add missing columns
            for col_def, col_default in columns_dict.items():
                col_name = col_def.split(' ')[0]
                if col_name not in existing_column_names:
                    await cursor.execute(f"ALTER TABLE {table_name} ADD {col_name} DEFAULT {col_default}")
                    await db.commit()

async def db_execute(db_path, execute_str, *args, exec_type='select', fetch='one'):
    """
    A function that is often used. It performs a single cursor.execute operation.
    If exec_type is 'select', the result from fetch is returned. If 'update', a commit is done.
    
    Parameters
    ----------
    db_path : str
        The path of the database.
    execute_str : str
        The string fed into aiosqlite.connect.cursor.execute.
    *args
        Args fed into cursor.execute(excute_str, (*args,))
    exec_type : ['select', 'update']
        If 'select', the result from fetch is returned. If 'update', a commit is done.
    fetch : ['one', 'all']
        If 'one', use cursor.fetchone(). If 'all', use cursor.fetchall()
    
    Returns
    -------
    result : tuple, None
        The result of cursor.fetchone() or cursor.fetchall(). If exec_type is 'update', return is None.
    """
    async with aiosqlite.connect(db_path) as db:
        async with db.cursor() as cursor:

            await cursor.execute(execute_str,(*args,))

            if exec_type == 'select':
                if fetch == 'one':
                    result = await cursor.fetchone()
                elif fetch == 'all':
                    result = await cursor.fetchall()
                else:
                    raise ValueError("Error in utils.database.db_execute: 'fetch'")
                return result
            
            elif exec_type == 'update':
                await db.commit()

            else:
                raise ValueError("Error in utils.database.db_execute: 'exec_type'")
