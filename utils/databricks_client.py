import os
import time
from typing import Dict, Any, List, Optional
from openai import OpenAI

class DatabricksClient:
    def __init__(self, model_configs):
        self.access_token = os.environ.get('DATABRICKS_ACCESS_TOKEN')
        self.base_url = "https://adb-6392715431242983.3.azuredatabricks.net/serving-endpoints"
        self.model_configs = model_configs
        
        # Initialize OpenAI client with Databricks configuration
        self.client = OpenAI(
            api_key=self.access_token,
            base_url=self.base_url
        )
        
        # Model mapping
        self.model_mapping = {
            "meta-llama-3-3-70b-instruct": "databricks-meta-llama-3-3-70b-instruct",
            "llama-4-maverick": "databricks-llama-4-maverick", 
            "meta-llama-3-1-405b-instruct": "databricks-meta-llama-3-1-405b-instruct"
        }

    def _build_messages(self, user_prompt: str, action: str, conversation_history: List[Dict] = None) -> List[Dict]:
        """Build messages in the format expected by the OpenAI API"""
        
        base_system_prompt = """You are an expert CI/CD engineer. Your role is to help users create optimal CI/CD pipelines by gathering all necessary information first.

Follow this process:
1. Analyze the user's initial request and conversation history
2. Identify missing information needed to create a complete CI/CD solution
3. Ask targeted, specific questions to gather: platform, branch strategy, deployment targets, testing requirements, security needs, etc.
4. Once all information is gathered, provide a comprehensive CI/CD solution

Always structure your responses to either:
- Ask clarifying questions when information is missing
- Provide the complete solution when all information is available

Focus on gathering these key details:
- CI/CD platform (GitHub Actions, GitLab CI, Jenkins, Azure DevOps, etc.)
- Source control platform and branch strategy
- Build tools and programming languages
- Testing requirements (unit tests, integration tests, security scans)
- Deployment targets (Kubernetes, AWS, Azure, GCP, Docker, etc.)
- Environment strategy (dev, staging, production)
- Security requirements (secrets management, vulnerability scanning)
- Notifications and monitoring

When asking questions:
- Be specific and technical
- Ask one set of related questions at a time
- Provide examples of what information you need
- Make it easy for the user to answer

When providing solutions:
- Give complete, runnable code
- Include explanations for key decisions
- Follow best practices for security and performance
- Provide configuration files and setup instructions"""

        system_prompts = {
            "generate": base_system_prompt,
            "optimize": base_system_prompt + "\n\nFor optimization requests, focus on identifying current pain points and improvement opportunities. Ask about current setup, performance issues, and goals.",
            "explain": base_system_prompt + "\n\nFor explanation requests, provide clear, educational content with examples and best practices."
        }
        
        system_prompt = system_prompts.get(action, system_prompts["generate"])
        
        messages = [
            {
                "role": "system",
                "content": system_prompt
            }
        ]
        
        # Add conversation history if provided
        if conversation_history:
            for message in conversation_history:
                # Only include user and assistant messages, not system messages
                if message["role"] in ["user", "assistant"]:
                    messages.append({
                        "role": message["role"],
                        "content": message["content"]
                    })
        
        # Add the current user prompt if not already in history
        if not conversation_history or conversation_history[-1]["content"] != user_prompt:
            messages.append({
                "role": "user", 
                "content": user_prompt
            })
        
        return messages

    def _needs_clarification(self, prompt: str, conversation_history: List[Dict] = None) -> bool:
        """Determine if we need to ask clarifying questions based on the prompt and history"""
        
        # Common CI/CD platforms that don't need clarification if specified
        platforms = ["github actions", "gitlab", "jenkins", "azure devops", "circleci", "travis", "bitbucket", "aws codebuild", "teamcity"]
        
        # Check if a specific platform is mentioned
        platform_mentioned = any(platform in prompt.lower() for platform in platforms)
        
        # Check if this looks like a follow-up answer to previous questions
        if conversation_history and len(conversation_history) > 0:
            last_assistant_message = None
            for msg in reversed(conversation_history):
                if msg["role"] == "assistant":
                    last_assistant_message = msg["content"]
                    break
            
            # If the last assistant message was asking questions, this might be an answer
            if last_assistant_message and any(q_word in last_assistant_message.lower() for q_word in ["?", "what", "which", "how", "when", "where", "could you", "can you", "please"]):
                return False
        
        # If no platform is specified and this seems like an initial request, ask for clarification
        return not platform_mentioned and len(prompt.split()) < 50

    def generate_code(self, prompt: str, model: str, action: str, conversation_history: List[Dict] = None) -> Dict[str, Any]:
        """Generate code or ask clarifying questions using Databricks model serving"""
        start_time = time.time()
        
        if model not in self.model_mapping:
            return {
                'success': False,
                'error': f"Model {model} not supported"
            }
        
        databricks_model_name = self.model_mapping[model]
        messages = self._build_messages(prompt, action, conversation_history)
        
        try:
            # Use the OpenAI client format that works with Databricks
            response = self.client.chat.completions.create(
                model=databricks_model_name,
                messages=messages,
                max_tokens=self.model_configs[model]['max_tokens'],
                temperature=self.model_configs[model]['temperature'],
                top_p=0.9,
                stop=["</s>"]
            )
            
            processing_time = time.time() - start_time
            
            generated_text = response.choices[0].message.content
            
            return {
                'success': True,
                'content': generated_text,
                'model_used': model,
                'processing_time': processing_time,
                'tokens_used': response.usage.total_tokens if response.usage else None,
                'needs_clarification': self._needs_clarification(prompt, conversation_history)
            }
            
        except Exception as e:
            processing_time = time.time() - start_time
            error_msg = str(e)
            
            # Provide more specific error messages
            if "401" in error_msg:
                error_msg = "Authentication failed. Please check your Databricks access token."
            elif "404" in error_msg:
                error_msg = f"Model endpoint not found. Please verify the model name: {databricks_model_name}"
            elif "429" in error_msg:
                error_msg = "Rate limit exceeded. Please try again later."
            elif "500" in error_msg or "503" in error_msg:
                error_msg = "Databricks service temporarily unavailable. Please try again later."
            elif "timeout" in error_msg.lower():
                error_msg = "Request timeout. The model is taking too long to respond."
                
            return {
                'success': False,
                'error': f"Model serving error: {error_msg}",
                'processing_time': processing_time
            }

    def check_model_availability(self) -> Dict[str, bool]:
        """Check availability of all models"""
        availability = {}
        for model_name, databricks_model_name in self.model_mapping.items():
            try:
                # Simple test to check if model is available
                test_response = self.client.chat.completions.create(
                    model=databricks_model_name,
                    messages=[{"role": "user", "content": "Say 'hello'"}],
                    max_tokens=10,
                    timeout=10
                )
                availability[model_name] = test_response.choices[0].message.content is not None
            except Exception:
                availability[model_name] = False
                
        return availability