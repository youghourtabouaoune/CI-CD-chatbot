import os
import time
from typing import Dict, Any
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

    def _build_messages(self, user_prompt: str, action: str) -> list:
        """Build messages in the format expected by the OpenAI API"""
        system_prompts = {
            "generate": """You are an expert CI/CD engineer. Generate clean, production-ready code for CI/CD pipelines. 
            Follow best practices for security, performance, and maintainability.
            Provide complete, runnable code with proper error handling and comments.
            Format code blocks with proper syntax highlighting.""",
            
            "optimize": """You are a CI/CD optimization specialist. Analyze and improve existing CI/CD configurations.
            Focus on performance, cost reduction, security improvements, and best practices.
            Provide specific, actionable optimizations with explanations and code examples.
            Include before/after examples when possible.""",
            
            "explain": """You are a CI/CD educator. Explain concepts clearly and comprehensively.
            Provide practical examples, best practices, and common pitfalls to avoid.
            Structure your explanation for easy understanding with clear headings and examples.
            Use analogies when helpful."""
        }
        
        system_prompt = system_prompts.get(action, system_prompts["generate"])
        
        return [
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user", 
                "content": user_prompt
            }
        ]

    def generate_code(self, prompt: str, model: str, action: str) -> Dict[str, Any]:
        """Generate code using Databricks model serving with OpenAI client"""
        start_time = time.time()
        
        if model not in self.model_mapping:
            return {
                'success': False,
                'error': f"Model {model} not supported"
            }
        
        databricks_model_name = self.model_mapping[model]
        messages = self._build_messages(prompt, action)
        
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
                'tokens_used': response.usage.total_tokens if response.usage else None
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