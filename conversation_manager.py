import os
import json
import time
from datetime import datetime
import uuid

class ConversationManager:
    def __init__(self, storage_dir="conversations"):
        self.storage_dir = storage_dir
        self.index_file = os.path.join(storage_dir, "index.json")
        
        # Ensure storage directory exists
        if not os.path.exists(storage_dir):
            os.makedirs(storage_dir)
            
        # Ensure index file exists
        if not os.path.exists(self.index_file):
            self._save_index([])

    def _load_index(self):
        try:
            with open(self.index_file, 'r') as f:
                return json.load(f)
        except Exception:
            return []

    def _save_index(self, index_data):
        try:
            with open(self.index_file, 'w') as f:
                json.dump(index_data, f, indent=2)
        except Exception as e:
            print(f"Error saving index file: {e}")

    def list_conversations(self, limit=30):
        """Returns a list of conversations sorted by updated_at (desc)."""
        index = self._load_index()
        # Sort by updated_at descending
        sorted_index = sorted(index, key=lambda x: x.get('updated_at', ''), reverse=True)
        return sorted_index[:limit]

    def get_conversation(self, session_id):
        """Returns the full conversation log for a session."""
        file_path = os.path.join(self.storage_dir, f"{session_id}.json")
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading conversation {session_id}: {e}")
                return []
        return []

    def save_message(self, session_id, role, content, conversation_title=None, extra_data=None):
        """
        Appends a message to the conversation log and updates the index.
        extra_data: Optional dict with additional fields like tableData, chartConfig, link, etc.
        """
        # 1. Update/Create Metadata in Index
        index = self._load_index()
        session_entry = next((item for item in index if item["id"] == session_id), None)
        
        now_iso = datetime.utcnow().isoformat() + "Z"

        if not session_entry:
            # New conversation
            title = conversation_title
            if not title:
                # Generate title from first user message if possible
                if role == 'user':
                    title = content[:50] + ("..." if len(content) > 50 else "")
                else:
                    title = "New Conversation"
            
            session_entry = {
                "id": session_id,
                "title": title,
                "created_at": now_iso,
                "updated_at": now_iso
            }
            index.append(session_entry)
        else:
            # Update existing
            session_entry["updated_at"] = now_iso
            # If we didn't have a good title before and this is a user message, maybe update it?
            # For now, let's keep the original title unless explicitly updated.
        
        self._save_index(index)

        # 2. Append Message to Log File
        file_path = os.path.join(self.storage_dir, f"{session_id}.json")
        messages = []
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r') as f:
                    messages = json.load(f)
            except Exception:
                messages = [] # corruption fallback
        
        new_message = {
            "role": role,
            "content": content,
            "timestamp": now_iso
        }
        
        # Merge extra data (tableData, chartConfig, link, thoughts, etc.)
        if extra_data and isinstance(extra_data, dict):
            new_message.update(extra_data)
        
        messages.append(new_message)
        
        try:
            with open(file_path, 'w') as f:
                json.dump(messages, f, indent=2)
        except Exception as e:
            print(f"Error saving conversation log {session_id}: {e}")

    def delete_conversation(self, session_id):
        """Deletes a conversation from the index and filesystem."""
        # Remove from index
        index = self._load_index()
        new_index = [item for item in index if item["id"] != session_id]
        self._save_index(new_index)
        
        # Remove file
        file_path = os.path.join(self.storage_dir, f"{session_id}.json")
        if os.path.exists(file_path):
            os.remove(file_path)
