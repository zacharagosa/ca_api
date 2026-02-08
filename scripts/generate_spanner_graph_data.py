
import csv
import random
import uuid
import sys
from datetime import datetime, timedelta

# Configuration
NUM_PLAYERS = 1000
NUM_CLANS = 50
NUM_ITEMS = 100
MAX_FRIENDS_PER_PLAYER = 10
CLAN_PARTICIPATION_RATE = 0.8
ITEM_OWNERSHIP_RATE = 0.9
MAX_ITEMS_PER_PLAYER = 20

OUTPUT_DIR = "datasets/spanner_graph"
import os
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Minimal Faker-like helpers
def random_date(start, end):
    """Generate a random datetime between `start` and `end`"""
    delta = end - start
    int_delta = (delta.days * 24 * 60 * 60) + delta.seconds
    random_second = random.randrange(int_delta)
    return start + timedelta(seconds=random_second)

def random_name():
    adjectives = ["Red", "Blue", "Fast", "Silent", "Shadow", "Epic", "Dark", "Light", "Neo", "Cyber"]
    nouns = ["Ninja", "Warrior", "Rider", "Storm", "Wolf", "Eagle", "Pilot", "Ghost", "Knight", "Dragon"]
    return f"{random.choice(adjectives)}{random.choice(nouns)}{random.randint(10, 99)}"

def random_clan_name():
    prefixes = ["The", "Team", "Clan", "Squad", "Order of"]
    names = ["Titans", "Legends", "Conquerors", "Assassins", "Kings", "Knights", "Vipers"]
    return f"{random.choice(prefixes)} {random.choice(names)}"

def random_item_name(type_):
    adls = ["Rusty", "Shiny", "Golden", "Ancient", "Cursed", "Blessed", "Neon"]
    if type_ == 'Weapon':
        nouns = ["Sword", "Axe", "Bow", "Dagger", "Staff"]
    elif type_ == 'Skin':
        nouns = ["Outfit", "Camo", "Suit", "Uniform"]
    else:
        nouns = ["Potion", "Elixir", "Scroll", "Orb"]
    return f"{random.choice(adls)} {random.choice(nouns)}"

def generate_data():
    print("Generating data (No Dependencies)...")
    
    now = datetime.now()
    two_years_ago = now - timedelta(days=730)
    three_years_ago = now - timedelta(days=1095)
    
    # 1. Players
    players = []
    for _ in range(NUM_PLAYERS):
        joined_at = random_date(two_years_ago, now)
        players.append({
            'player_id': str(uuid.uuid4()),
            'gamertag': random_name(),
            'region': random.choice(['NA', 'EU', 'APAC', 'LATAM']),
            'joined_at': joined_at,
            'account_level': random.randint(1, 100)
        })
    print(f"Generated {len(players)} players.")

    # 2. Clans
    clans = []
    for _ in range(NUM_CLANS):
        clans.append({
            'clan_id': str(uuid.uuid4()),
            'clan_name': random_clan_name(),
            'created_at': random_date(three_years_ago, two_years_ago)
        })
    print(f"Generated {len(clans)} clans.")

    # 3. Items
    items = []
    item_types = ['Weapon', 'Skin', 'Consumable', 'Vehicle']
    rarities = ['Common', 'Rare', 'Epic', 'Legendary']
    for _ in range(NUM_ITEMS):
        itype = random.choice(item_types)
        items.append({
            'item_id': str(uuid.uuid4()),
            'item_name': random_item_name(itype),
            'rarity': random.choices(rarities, weights=[50, 30, 15, 5])[0],
            'type': itype
        })
    print(f"Generated {len(items)} items.")

    # 4. Friendships (Edges)
    friendships = []
    for player in players:
        num_friends = random.randint(0, MAX_FRIENDS_PER_PLAYER)
        # Random sample of other players
        friends = random.sample(players, k=min(num_friends, len(players)))
        for friend in friends:
            if player['player_id'] == friend['player_id']:
                continue
            
            friendships.append({
                'initiator_id': player['player_id'],
                'acceptor_id': friend['player_id'],
                'created_at': random_date(player['joined_at'], now)
            })
    print(f"Generated {len(friendships)} friendships.")

    # 5. Clan Memberships (Edges)
    clan_memberships = []
    for player in players:
        if random.random() < CLAN_PARTICIPATION_RATE:
            clan = random.choice(clans)
            role = 'Leader' if random.random() < 0.05 else 'Member'
            # Ensure join date is after clan creation AND player join
            start_date = max(player['joined_at'], clan['created_at'])
            if start_date < now:
                join_date = random_date(start_date, now)
                clan_memberships.append({
                    'player_id': player['player_id'],
                    'clan_id': clan['clan_id'],
                    'role': role,
                    'joined_at': join_date
                })
    print(f"Generated {len(clan_memberships)} clan memberships.")

    # 6. Inventory (Edges)
    inventory = []
    for player in players:
        if random.random() < ITEM_OWNERSHIP_RATE:
            num_items = random.randint(1, MAX_ITEMS_PER_PLAYER)
            owned_items = random.choices(items, k=num_items)
            for item in owned_items:
                inventory.append({
                    'player_id': player['player_id'],
                    'item_id': item['item_id'],
                    'acquired_at': random_date(player['joined_at'], now),
                    'acquisition_source': random.choice(['Purchase', 'Drop', 'Trade', 'Gift'])
                })
    print(f"Generated {len(inventory)} inventory items.")

    return {
        'Players': players,
        'Clans': clans,
        'Items': items,
        'Friendships': friendships,
        'ClanMemberships': clan_memberships,
        'Inventory': inventory
    }

def write_sql(data):
    filepath = os.path.join(OUTPUT_DIR, "schema_and_data.sql")
    with open(filepath, 'w') as f:
        f.write("-- Spanner Graph Schema and Data\n\n")
        
        # DDL
        f.write("-- 1. Create Node Tables\n")
        f.write("CREATE TABLE Players (\n  player_id STRING(36) NOT NULL,\n  gamertag STRING(MAX),\n  region STRING(MAX),\n  joined_at TIMESTAMP,\n  account_level INT64\n) PRIMARY KEY (player_id);\n\n")
        f.write("CREATE TABLE Clans (\n  clan_id STRING(36) NOT NULL,\n  clan_name STRING(MAX),\n  created_at TIMESTAMP\n) PRIMARY KEY (clan_id);\n\n")
        f.write("CREATE TABLE Items (\n  item_id STRING(36) NOT NULL,\n  item_name STRING(MAX),\n  rarity STRING(MAX),\n  type STRING(MAX)\n) PRIMARY KEY (item_id);\n\n")
        
        f.write("-- 2. Create Edge Tables\n")
        f.write("CREATE TABLE Friendships (\n  initiator_id STRING(36) NOT NULL,\n  acceptor_id STRING(36) NOT NULL,\n  created_at TIMESTAMP,\n  CONSTRAINT FK_Friend_Initiator FOREIGN KEY (initiator_id) REFERENCES Players (player_id),\n  CONSTRAINT FK_Friend_Acceptor FOREIGN KEY (acceptor_id) REFERENCES Players (player_id)\n) PRIMARY KEY (initiator_id, acceptor_id);\n\n")
        f.write("CREATE TABLE ClanMemberships (\n  player_id STRING(36) NOT NULL,\n  clan_id STRING(36) NOT NULL,\n  role STRING(MAX),\n  joined_at TIMESTAMP,\n  CONSTRAINT FK_Clan_Player FOREIGN KEY (player_id) REFERENCES Players (player_id),\n  CONSTRAINT FK_Clan_Clan FOREIGN KEY (clan_id) REFERENCES Clans (clan_id)\n) PRIMARY KEY (player_id, clan_id);\n\n")
        f.write("CREATE TABLE Inventory (\n  player_id STRING(36) NOT NULL,\n  item_id STRING(36) NOT NULL,\n  acquired_at TIMESTAMP,\n  acquisition_source STRING(MAX),\n  CONSTRAINT FK_Inv_Player FOREIGN KEY (player_id) REFERENCES Players (player_id),\n  CONSTRAINT FK_Inv_Item FOREIGN KEY (item_id) REFERENCES Items (item_id)\n) PRIMARY KEY (player_id, item_id, acquired_at);\n\n") 
        
        f.write("-- 3. Create Property Graph\n")
        f.write("CREATE PROPERTY GRAPH GamingGraph\n")
        f.write("  NODE TABLES (\n    Players,\n    Clans,\n    Items\n  )\n")
        f.write("  EDGE TABLES (\n")
        f.write("    Friendships\n      SOURCE KEY (initiator_id) REFERENCES Players (player_id)\n      DESTINATION KEY (acceptor_id) REFERENCES Players (player_id)\n      LABEL IS_FRIEND,\n")
        f.write("    ClanMemberships\n      SOURCE KEY (player_id) REFERENCES Players (player_id)\n      DESTINATION KEY (clan_id) REFERENCES Clans (clan_id)\n      LABEL MEMBER_OF,\n")
        f.write("    Inventory\n      SOURCE KEY (player_id) REFERENCES Players (player_id)\n      DESTINATION KEY (item_id) REFERENCES Items (item_id)\n      LABEL OWNS\n  );\n\n")

        # DML
        f.write("-- 4. Data Insertion (Sample)\n")
        
        def escape(s):
            if isinstance(s, datetime):
                return f"TIMESTAMP('{s.isoformat()}')"
            if isinstance(s, int):
                return str(s)
            escaped = str(s).replace("'", "\\'")
            return f"'{escaped}'"

        for table, rows in data.items():
            if not rows: continue
            keys = rows[0].keys()
            cols = ", ".join(keys)
            
            f.write(f"\n-- Data for {table}\n")
            
            chunk_size = 50
            for i in range(0, len(rows), chunk_size):
                chunk = rows[i:i+chunk_size]
                values_list = []
                for row in chunk:
                    vals = ", ".join([escape(row[k]) for k in keys])
                    values_list.append(f"({vals})")
                
                f.write(f"INSERT INTO {table} ({cols}) VALUES\n")
                f.write(",\n".join(values_list))
                f.write(";\n")

    print(f"SQL file written to {filepath}")

def main():
    data = generate_data()
    write_sql(data)
    print("Done.")

if __name__ == "__main__":
    main()
