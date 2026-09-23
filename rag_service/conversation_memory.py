"""
Conversation Memory Module for Session-Aware RAG
Implements conversation buffer memory and history-aware query reformulation
"""

import uuid
from datetime import datetime


class ConversationMemory:
    """Manages conversation history and context for RAG queries"""
    
    def __init__(self):
        # session_id -> conversation history
        self.sessions: dict[str, list[dict]] = {}
        # session_id -> metadata
        self.session_metadata: dict[str, dict] = {}
        print("[ConversationMemory] Initialized")
    
    def create_session(self) -> str:
        """
        Create a new conversation session
        
        Returns:
            session_id: Unique session identifier
        """
        session_id = str(uuid.uuid4())
        self.sessions[session_id] = []
        self.session_metadata[session_id] = {
            "created_at": datetime.now().isoformat(),
            "last_activity": datetime.now().isoformat(),
            "message_count": 0
        }
        print(f"[ConversationMemory] Created session: {session_id}")
        return session_id
    
    def add_message(self, session_id: str, role: str, content: str):
        """
        Add a message to conversation history
        
        Args:
            session_id: Session identifier
            role: 'user' or 'assistant'
            content: Message content
        """
        if session_id not in self.sessions:
            print(f"[ConversationMemory] Session {session_id} not found, creating new session")
            self.sessions[session_id] = []
            self.session_metadata[session_id] = {
                "created_at": datetime.now().isoformat(),
                "last_activity": datetime.now().isoformat(),
                "message_count": 0
            }
        
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        }
        
        self.sessions[session_id].append(message)
        self.session_metadata[session_id]["last_activity"] = datetime.now().isoformat()
        self.session_metadata[session_id]["message_count"] += 1
    
    def get_history(self, session_id: str, max_messages: int = 10) -> list[dict]:
        """
        Get conversation history for a session
        
        Args:
            session_id: Session identifier
            max_messages: Maximum number of recent messages to return
            
        Returns:
            List of message dictionaries
        """
        if session_id not in self.sessions:
            return []
        
        # Return most recent messages
        return self.sessions[session_id][-max_messages:]
    
    def get_context_string(self, session_id: str, max_messages: int = 6) -> str:
        """
        Get conversation history as formatted string for LLM context
        
        Args:
            session_id: Session identifier
            max_messages: Maximum number of recent messages to include
            
        Returns:
            Formatted conversation history string
        """
        history = self.get_history(session_id, max_messages)
        
        if not history:
            return ""
        
        context_parts = []
        for msg in history:
            role = "User" if msg["role"] == "user" else "Assistant"
            context_parts.append(f"{role}: {msg['content']}")
        
        return "\n".join(context_parts)
    
    def reformulate_query(self, session_id: str, current_query: str) -> str:
        """
        Reformulate query based on conversation history to create standalone question
        
        Args:
            session_id: Session identifier
            current_query: Current user query
            
        Returns:
            Reformulated standalone query
        """
        history = self.get_history(session_id, max_messages=4)
        
        # Never reformulate greetings, capability questions, or conversational queries
        query_lower = current_query.lower().strip()
        import re
        meta_patterns = [
            r'\bwhat\s+(?:can|do)\s+(?:you|u)\s+do\b',
            r'\bwho\s+(?:are|r)\s+(?:you|u)\b',
            r'\bwhat\s+(?:are|r)\s+(?:you|u)\b',
            r'\bhow\s+can\s+(?:you|u)\s+help\b',
            r'\b(?:capabilities|features)\b',
            r'^(?:hello|hi|hey|namaste|thanks|thank\s+you|ok|okay|bye|good\s+morning|good\s+afternoon|good\s+evening)\b',
            r'\bwho\s+made\s+you\b'
        ]
        if any(re.search(pat, query_lower) for pat in meta_patterns):
            return current_query

        # If no history or query is already detailed, return as-is
        if not history or len(current_query.split()) > 10:
            return current_query
        
        # Check if query is an explicit follow-up referencing previous context
        follow_up_patterns = [
            r'\b(its|this|that|these|those)\b',
            r'\bwhat about\b',
            r'\bhow about\b',
            r'\band (what|how|why|is)\b',
            r'\bis it (bailable|compoundable|cognizable)\b',
            r'\bwhat is the punishment for (it|that|this)\b'
        ]
        import re
        is_follow_up = any(re.search(pat, query_lower) for pat in follow_up_patterns)
        
        # Only reformulate if it's an explicit follow-up
        if not is_follow_up:
            return current_query
        
        # Extract context from last user-assistant exchange
        last_user_query = None
        last_topic = None
        
        for msg in reversed(history):
            if msg["role"] == "user" and not last_user_query:
                last_user_query = msg["content"]
            if msg["role"] == "assistant" and not last_topic:
                content = msg["content"].lower()
                bns_match = re.search(r'bns\s+section\s+\d+', content)
                ipc_match = re.search(r'ipc\s+section\s+\d+', content)
                
                if bns_match:
                    last_topic = bns_match.group(0).upper()
                elif ipc_match:
                    last_topic = ipc_match.group(0).upper()
        
        # Reformulate query with context only for true follow-ups
        if last_topic:
            reformulated = f"{current_query} (in context of {last_topic})"
        elif last_user_query:
            reformulated = f"{current_query} (related to: {last_user_query[:40]})"
        else:
            reformulated = current_query
        
        print(f"[ConversationMemory] Follow-up reformulated: '{current_query}' -> '{reformulated}'")
        return reformulated
    
    def clear_session(self, session_id: str):
        """
        Clear conversation history for a session
        
        Args:
            session_id: Session identifier
        """
        if session_id in self.sessions:
            self.sessions[session_id] = []
            self.session_metadata[session_id]["last_activity"] = datetime.now().isoformat()
            self.session_metadata[session_id]["message_count"] = 0
            print(f"[ConversationMemory] Cleared session: {session_id}")
    
    def delete_session(self, session_id: str):
        """
        Delete a session completely
        
        Args:
            session_id: Session identifier
        """
        if session_id in self.sessions:
            del self.sessions[session_id]
            del self.session_metadata[session_id]
            print(f"[ConversationMemory] Deleted session: {session_id}")
    
    def get_session_info(self, session_id: str) -> dict | None:
        """
        Get metadata about a session
        
        Args:
            session_id: Session identifier
            
        Returns:
            Session metadata or None if not found
        """
        return self.session_metadata.get(session_id)
    
    def cleanup_old_sessions(self, max_age_hours: int = 24):
        """
        Remove sessions older than specified hours
        
        Args:
            max_age_hours: Maximum age in hours
        """
        from datetime import timedelta
        
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        sessions_to_delete = []
        
        for session_id, metadata in self.session_metadata.items():
            last_activity = datetime.fromisoformat(metadata["last_activity"])
            if last_activity < cutoff_time:
                sessions_to_delete.append(session_id)
        
        for session_id in sessions_to_delete:
            self.delete_session(session_id)
        
        if sessions_to_delete:
            print(f"[ConversationMemory] Cleaned up {len(sessions_to_delete)} old sessions")
