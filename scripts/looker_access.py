#!/usr/bin/env python3
"""
Looker Access Management Script

Grants or revokes access to Looker content by adding/removing users from a specified group.
Uses the Looker SDK with credentials from environment variables.

Usage:
    python scripts/looker_access.py grant user@example.com
    python scripts/looker_access.py revoke user@example.com
    python scripts/looker_access.py list
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_sdk():
    """Initialize Looker SDK with environment credentials."""
    import looker_sdk
    
    # Try dataset-specific credentials first (EVENTS dataset), then generic
    dataset_name = os.getenv("DATASET_NAME", "events").upper()
    
    # Get Looker instance URI from dataset config or direct env var
    looker_uri = os.getenv("LOOKER_INSTANCE_URI")
    if not looker_uri:
        # Default to the gaming Looker instance
        looker_uri = "https://3417a175-fe20-4370-974f-2f2b535340ab.looker.app"
    
    # Try dataset-specific credentials first
    client_id = os.getenv(f"LOOKER_CLIENT_ID_{dataset_name}") or os.getenv("LOOKER_CLIENT_ID")
    client_secret = os.getenv(f"LOOKER_CLIENT_SECRET_{dataset_name}") or os.getenv("LOOKER_CLIENT_SECRET")
    
    if not client_id or not client_secret:
        raise ValueError(f"Missing Looker credentials. Set LOOKER_CLIENT_ID_{dataset_name} and LOOKER_CLIENT_SECRET_{dataset_name} in .env")
    
    # Set SDK env vars
    os.environ["LOOKERSDK_BASE_URL"] = looker_uri
    os.environ["LOOKERSDK_CLIENT_ID"] = client_id
    os.environ["LOOKERSDK_CLIENT_SECRET"] = client_secret
    
    return looker_sdk.init40()


def find_or_create_group(sdk, group_name="Gaming Analytics Users"):
    """Find a group by name, or create it if it doesn't exist."""
    from looker_sdk import models40
    
    # Search for existing group
    groups = sdk.search_groups(name=group_name)
    if groups:
        return groups[0]
    
    # Create new group
    print(f"Creating Looker group: {group_name}")
    new_group = sdk.create_group(body=models40.WriteGroup(name=group_name))
    return new_group


def find_user_by_email(sdk, email):
    """Find a Looker user by email address."""
    users = sdk.search_users(email=email)
    if users:
        return users[0]
    return None


def create_user(sdk, email):
    """Create a new Looker user with the given email.
    
    Note: On Looker (Google Cloud core), users must sign in via Google SSO first
    to be auto-provisioned. This function will fail on those instances.
    """
    from looker_sdk import models40
    
    print(f"Creating new Looker user: {email}")
    
    try:
        # Create user
        user = sdk.create_user(body=models40.WriteUser(
            first_name=email.split("@")[0],
            last_name="(Auto-provisioned)",
            is_disabled=False
        ))
        
        # Add email credential (may fail on Looker Cloud Core)
        sdk.create_user_credentials_email(user.id, body=models40.WriteCredentialsEmail(email=email))
        
        return user
    except Exception as e:
        if "Unsupported in Looker (Google Cloud core)" in str(e):
            print(f"⚠️  Cannot create user via API on Looker (Google Cloud core).")
            print(f"   The user must sign into Looker directly first to be auto-provisioned.")
            print(f"   After they sign in once, run this script again to add them to the group.")
            return None
        raise e


def grant_access(email, group_name="Gaming Analytics Users"):
    """Grant a user access to Looker by adding them to the specified group."""
    sdk = get_sdk()
    
    # Find or create the group
    group = find_or_create_group(sdk, group_name)
    print(f"Using group: {group.name} (ID: {group.id})")
    
    # Find or create the user
    user = find_user_by_email(sdk, email)
    if not user:
        user = create_user(sdk, email)
        if not user:
            # Creation failed (e.g., Looker Cloud Core) - user needs to sign in first
            return False
    
    print(f"User: {user.first_name} {user.last_name} (ID: {user.id})")
    
    # Check if already in group by getting group members
    group_users = sdk.all_group_users(group.id)
    if any(u.id == user.id for u in group_users):
        print(f"✅ User {email} is already in group '{group_name}'")
        return True
    
    # Add user to group
    sdk.add_group_user(group.id, body={"user_id": user.id})
    print(f"✅ Added {email} to Looker group '{group_name}'")
    return True


def revoke_access(email, group_name="Gaming Analytics Users"):
    """Remove a user from the specified Looker group."""
    sdk = get_sdk()
    
    # Find the group
    groups = sdk.search_groups(name=group_name)
    if not groups:
        print(f"Group '{group_name}' not found")
        return False
    group = groups[0]
    
    # Find the user
    user = find_user_by_email(sdk, email)
    if not user:
        print(f"User {email} not found in Looker")
        return False
    
    # Remove from group
    try:
        sdk.delete_group_user(group.id, user.id)
        print(f"✅ Removed {email} from Looker group '{group_name}'")
        return True
    except Exception as e:
        print(f"Error removing user: {e}")
        return False


def list_group_members(group_name="Gaming Analytics Users"):
    """List all members of the specified Looker group."""
    sdk = get_sdk()
    
    # Find the group
    groups = sdk.search_groups(name=group_name)
    if not groups:
        print(f"Group '{group_name}' not found")
        return
    group = groups[0]
    
    print(f"Members of '{group_name}' (ID: {group.id}):")
    print("-" * 40)
    
    users = sdk.all_group_users(group.id)
    if not users:
        print("  (no members)")
    for user in users:
        # Get email
        try:
            creds = sdk.user_credentials_email(user.id)
            email = creds.email if creds else "(no email)"
        except:
            email = "(no email)"
        print(f"  {user.first_name} {user.last_name} - {email}")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    action = sys.argv[1].lower()
    
    if action == "grant" and len(sys.argv) >= 3:
        email = sys.argv[2]
        grant_access(email)
    elif action == "revoke" and len(sys.argv) >= 3:
        email = sys.argv[2]
        revoke_access(email)
    elif action == "list":
        list_group_members()
    else:
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
