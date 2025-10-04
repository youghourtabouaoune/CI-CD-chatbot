from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum

class ModelChoice(str, Enum):
    META_LLAMA_3_70B = "meta-llama-3-3-70b-instruct"
    LLAMA_4_MAVERICK = "llama-4-maverick" 
    META_LLAMA_3_405B = "meta-llama-3-1-405b-instruct"

class ActionType(str, Enum):
    GENERATE = "generate"
    OPTIMIZE = "optimize"
    EXPLAIN = "explain"

class CodeGenerationRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=4000, description="User prompt for code generation")
    model: ModelChoice = Field(default=ModelChoice.META_LLAMA_3_70B, description="Selected model")
    action: ActionType = Field(default=ActionType.GENERATE, description="Type of action")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Additional context")
    
    class Config:
        json_schema_extra = {
            "example": {
                "prompt": "Create a GitHub Actions workflow for a Node.js application",
                "model": "meta-llama-3-3-70b-instruct",
                "action": "generate"
            }
        }

class CodeGenerationResponse(BaseModel):
    success: bool
    content: str
    model_used: str
    tokens_used: Optional[int] = None
    processing_time: float
    error: Optional[str] = None

class DocumentUploadResponse(BaseModel):
    success: bool
    filename: str
    file_url: str
    file_size: int
    message: str
    error: Optional[str] = None

class HealthResponse(BaseModel):
    status: str
    timestamp: str
    version: str
    models_available: List[str]