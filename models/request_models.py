from typing import List, Optional, Dict, Any
from pydantic import BaseModel, EmailStr
from enum import Enum

class ModelType(str, Enum):
    CLAUDE_4_1_OPUC = "claude-opus-4-1"
    LLAMA_3_70B = "meta-llama-3-3-70b-instruct"
    LLAMA_4_MAVERICK = "llama-4-maverick"
    LLAMA_3_1_405B = "meta-llama-3-1-405b-instruct"
    DEEPSEEK_CODER = "deepseek-coder"
    DEEPSEEK_CHAT = "deepseek-chat"

class ActionType(str, Enum):
    GENERATE = "generate"
    OPTIMIZE = "optimize"
    EXPLAIN = "explain"

class MessageRole(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"

class ConversationMessage(BaseModel):
    role: MessageRole
    content: str
    timestamp: Optional[str] = None

class CodeGenerationRequest(BaseModel):
    prompt: str
    model: ModelType
    action: ActionType
    conversation_history: Optional[List[Dict[str, Any]]] = None

class CodeGenerationResponse(BaseModel):
    success: bool
    content: str
    model_used: str
    processing_time: float
    tokens_used: Optional[int] = None
    error: Optional[str] = None
    needs_clarification: bool = False

class DocumentUploadResponse(BaseModel):
    success: bool
    filename: str
    file_url: str
    file_size: int
    message: str

class HealthResponse(BaseModel):
    status: str
    timestamp: str
    version: str
    models_available: List[str]

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class SignupRequest(BaseModel):
    email: EmailStr
    password: str
    first_name: str
    last_name: str