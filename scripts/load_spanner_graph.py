
import os
import time
from google.cloud import spanner
from generate_spanner_graph_data import generate_data
from datetime import datetime

INSTANCE_ID = "gaming-instance"
DATABASE_ID = "gaming-graph"
PROJECT_ID = "aragosalooker"

def load_ddl(instance, database_id):
    print("Creating schema...")
    database = instance.database(database_id)
    
    # We define DDL here directly to ensure we have control, 
    # OR we could parse the SQL file. Defining here is safer for the script.
    # Note: We are NOT using Property Graph DDL in the standard DDL update 
    # unless 'ISO GQL' is enabled or we use the specific PG syntax supported by GoogleSQL.
    # Spanner GoogleSQL supports CREATE PROPERTY GRAPH.
    
    ddl_statements = [
        """CREATE TABLE Players (
            player_id STRING(36) NOT NULL,
            gamertag STRING(MAX),
            region STRING(MAX),
            joined_at TIMESTAMP,
            account_level INT64
        ) PRIMARY KEY (player_id)""",
        
        """CREATE TABLE Clans (
            clan_id STRING(36) NOT NULL,
            clan_name STRING(MAX),
            created_at TIMESTAMP
        ) PRIMARY KEY (clan_id)""",
        
        """CREATE TABLE Items (
            item_id STRING(36) NOT NULL,
            item_name STRING(MAX),
            rarity STRING(MAX),
            type STRING(MAX)
        ) PRIMARY KEY (item_id)""",
        
        """CREATE TABLE Friendships (
            initiator_id STRING(36) NOT NULL,
            acceptor_id STRING(36) NOT NULL,
            created_at TIMESTAMP,
            CONSTRAINT FK_Friend_Initiator FOREIGN KEY (initiator_id) REFERENCES Players (player_id),
            CONSTRAINT FK_Friend_Acceptor FOREIGN KEY (acceptor_id) REFERENCES Players (player_id)
        ) PRIMARY KEY (initiator_id, acceptor_id)""",
        
        """CREATE TABLE ClanMemberships (
            player_id STRING(36) NOT NULL,
            clan_id STRING(36) NOT NULL,
            role STRING(MAX),
            joined_at TIMESTAMP,
            CONSTRAINT FK_Clan_Player FOREIGN KEY (player_id) REFERENCES Players (player_id),
            CONSTRAINT FK_Clan_Clan FOREIGN KEY (clan_id) REFERENCES Clans (clan_id)
        ) PRIMARY KEY (player_id, clan_id)""",
        
        """CREATE TABLE Inventory (
            player_id STRING(36) NOT NULL,
            item_id STRING(36) NOT NULL,
            acquired_at TIMESTAMP,
            acquisition_source STRING(MAX),
            CONSTRAINT FK_Inv_Player FOREIGN KEY (player_id) REFERENCES Players (player_id),
            CONSTRAINT FK_Inv_Item FOREIGN KEY (item_id) REFERENCES Items (item_id)
        ) PRIMARY KEY (player_id, item_id, acquired_at)""",
        
        """CREATE PROPERTY GRAPH GamingGraph
          NODE TABLES (
            Players,
            Clans,
            Items
          )
          EDGE TABLES (
            Friendships
              SOURCE KEY (initiator_id) REFERENCES Players (player_id)
              DESTINATION KEY (acceptor_id) REFERENCES Players (player_id)
              LABEL IS_FRIEND,
            ClanMemberships
              SOURCE KEY (player_id) REFERENCES Players (player_id)
              DESTINATION KEY (clan_id) REFERENCES Clans (clan_id)
              LABEL MEMBER_OF,
            Inventory
              SOURCE KEY (player_id) REFERENCES Players (player_id)
              DESTINATION KEY (item_id) REFERENCES Items (item_id)
              LABEL OWNS
          )"""
    ]
    
    operation = database.update_ddl(ddl_statements)
    print("Waiting for DDL to complete...")
    operation.result(1200) # Wait up to 20 minutes
    print("Schema created.")

def insert_batch(transaction, table, rows, columns):
    # Convert dict rows to list of values in correct order
    values = []
    for row in rows:
        values.append([row[col] for col in columns])
    transaction.insert(table, columns=columns, values=values)

def load_data(instance, database_id):
    print("Generating data...")
    data = generate_data()
    
    client = spanner.Client(project=PROJECT_ID)
    instance = client.instance(INSTANCE_ID)
    database = instance.database(DATABASE_ID)

    print("Inserting data...")
    
    # Tables and their columns in order
    tables_map = {
        'Players': ['player_id', 'gamertag', 'region', 'joined_at', 'account_level'],
        'Clans': ['clan_id', 'clan_name', 'created_at'],
        'Items': ['item_id', 'item_name', 'rarity', 'type'],
        'Friendships': ['initiator_id', 'acceptor_id', 'created_at'],
        'ClanMemberships': ['player_id', 'clan_id', 'role', 'joined_at'],
        'Inventory': ['player_id', 'item_id', 'acquired_at', 'acquisition_source']
    }

    # Ordering is important for FK constraints: Nodes first, then Edges
    order = ['Players', 'Clans', 'Items', 'Friendships', 'ClanMemberships', 'Inventory']
    
    for table in order:
        rows = data.get(table, [])
        if not rows: continue
        
        cols = tables_map[table]
        print(f"Inserting {len(rows)} rows into {table}...")
        
        # Batch insert in chunks of 500
        chunk_size = 500
        for i in range(0, len(rows), chunk_size):
            chunk = rows[i:i+chunk_size]
            with database.batch() as batch:
                 batch.insert(
                    table=table,
                    columns=cols,
                    values=[[row[c] for c in cols] for row in chunk]
                )
    print("Data insertion complete.")

def main():
    client = spanner.Client(project=PROJECT_ID)
    instance = client.instance(INSTANCE_ID)
    
    # Check if DB exists, if not created (though we created via gcloud)
    # We assume it exists but might be empty schema if gcloud succeeded but DDL not run?
    # gcloud create db doesn't run DDL unless specified.
    
    # We will try to update DDL. If tables exist, it might fail or we should catch.
    # For now, we assume fresh DB from 'gcloud databases create' which makes an empty DB.
    
    try:
        load_ddl(instance, DATABASE_ID)
    except Exception as e:
        print(f"DDL Update failed (maybe already exists?): {e}")
        # Continue to data load
    
    load_data(instance, DATABASE_ID)
    print("Done.")

if __name__ == "__main__":
    main()
