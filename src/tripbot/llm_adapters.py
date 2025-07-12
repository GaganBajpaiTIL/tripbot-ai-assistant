import os
import json
import logging
from typing import Dict, Any, Optional
import google.generativeai as genai
from openai import OpenAI
import boto3
from botocore.exceptions import ClientError, NoCredentialsError

logger = logging.getLogger(__name__)

class LLMAdapter:
    """Base class for LLM adapters"""
    
    def generate_response(self, messages: list, system_prompt: str = None) -> str:
        """Generate a response from the LLM"""
        raise NotImplementedError

class OpenAIAdapter(LLMAdapter):
    """OpenAI GPT adapter for conversational trip planning"""
    
    def __init__(self):
        self.api_key = os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            logger.warning("OpenAI API key not found")
            self.client = None
        else:
            self.client = OpenAI(api_key=self.api_key)
    
    def generate_response(self, messages: list, system_prompt: str = None) -> str:
        """Generate response using OpenAI GPT-4o"""
        if not self.client:
            return "I'm sorry, but I'm having trouble connecting to my language processing service. Please try again later."
        
        try:
            # The newest OpenAI model is "gpt-4o" which was released May 13, 2024.
            # Do not change this unless explicitly requested by the user
            chat_messages = []
            
            if system_prompt:
                chat_messages.append({"role": "system", "content": system_prompt})
            
            chat_messages.extend(messages)
            
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=chat_messages,
                max_tokens=500,
                temperature=0.7
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            return "I apologize, but I'm experiencing some technical difficulties. Please try again in a moment."

class GeminiAdapter(LLMAdapter):
    """Google Gemini adapter for conversational trip planning"""
    
    def __init__(self):
        self.api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not self.api_key:
            logger.warning("Gemini API key not found")
            self.model = None
        else:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel('gemini-pro')
    
    def generate_response(self, messages: list, system_prompt: str = None) -> str:
        """Generate response using Google Gemini"""
        if not self.model:
            return "I'm sorry, but I'm having trouble connecting to my language processing service. Please try again later."
        
        try:
            # Convert messages to Gemini format
            conversation_text = ""
            if system_prompt:
                conversation_text += f"System: {system_prompt}\n\n"
            
            for message in messages:
                role = "Human" if message["role"] == "user" else "Assistant"
                conversation_text += f"{role}: {message['content']}\n"
            
            conversation_text += "Assistant: "
            
            response = self.model.generate_content(conversation_text)
            return response.text
            
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            return "I apologize, but I'm experiencing some technical difficulties. Please try again in a moment."

class BedrockLlamaAdapter(LLMAdapter):
    """AWS Bedrock Llama adapter for conversational trip planning"""
    
    def __init__(self):
        
        try:
            self.client = boto3.client('bedrock-runtime')
            logger.info("AWS Bedrock connection successful")
        except (ClientError, NoCredentialsError) as e:
            logger.warning(f"AWS Bedrock connection failed: {e}")
            self.client = None
        except Exception as e:
            logger.exception("Unexpected error initializing AWS Bedrock client")
            self.client = None
    
    def generate_response(self, messages: list, system_prompt: str = None) -> str:
        """Generate response using AWS Bedrock Llama models"""
        if not self.client:
            error_msg = "AWS Bedrock client not initialized. Check AWS credentials and configuration."
            logger.error(error_msg)
            return "I'm sorry, but I'm having trouble connecting to my language processing service. Please try again later."
        
        try:
            # Log the incoming request
            logger.debug(f"Generating response with system prompt: {system_prompt}")
            logger.debug(f"Messages: {json.dumps(messages, indent=2)}")
            
            # Convert messages to Llama format
            conversation_text = ""
            if system_prompt:
                conversation_text += f"System: {system_prompt}\n\n"
            
            for message in messages:
                role = "Human" if message["role"] == "user" else "Assistant"
                conversation_text += f"{role}: {message['content']}\n"
            
            conversation_text += "Assistant: "
            
            # Get model ID from environment variable or use default
            model_id = os.environ.get('AWS_MODEL_ID', 'meta.llama3-70b-instruct-v1:0')
            logger.debug(f"Using model ID: {model_id}")
            
            body = json.dumps({
                "prompt": conversation_text,
                "max_gen_len": 500,
                "temperature": 0.7,
                "top_p": 0.9
            })
            
            logger.debug(f"Sending request to model {model_id} with body: {body[:500]}...")
            
            try:
                #TODO: Use converse API instead.
                response = self.client.invoke_model(
                    modelId=model_id,
                    body=body,
                    contentType='application/json',
                    accept='application/json'
                )
                
                response_body = json.loads(response['body'].read())
                logger.debug(f"Received response: {json.dumps(response_body, indent=2)[:500]}...")
                
                if 'generation' not in response_body:
                    logger.warning(f"Unexpected response format: {response_body}")
                    return "I apologize, but I received an unexpected response format from the language model."
                    
                return response_body['generation']
                
            except ClientError as e:
                error_code = e.response.get('Error', {}).get('Code', 'Unknown')
                error_message = e.response.get('Error', {}).get('Message', 'No error message')
                logger.error(f"AWS Bedrock API error - Code: {error_code}, Message: {error_message}")
                
                if error_code == 'AccessDeniedException':
                    return "I don't have permission to access the language model. Please check your AWS permissions."
                elif error_code == 'ResourceNotFoundException':
                    return "The requested language model was not found. Please check the model ID."
                elif error_code == 'ThrottlingException':
                    return "The service is currently experiencing high traffic. Please try again in a moment."
                else:
                    return f"I encountered an error with the language model: {error_message}"
            
        except Exception as e:
            logger.exception("Unexpected error in generate_response")
            return "I apologize, but I'm experiencing some technical difficulties. Please try again in a moment."

class TripPlannerBot:
    """Main trip planner bot with conversation management"""
    
    def __init__(self, preferred_llm: str = "openai"):
        self.preferred_llm = preferred_llm.lower()
        self.openai_adapter = None
        self.gemini_adapter = None
        self.bedrock_adapter = None
        
        # Initialize only the requested adapter
        if self.preferred_llm == "openai":
            self.openai_adapter = OpenAIAdapter()
        elif self.preferred_llm == "gemini":
            self.gemini_adapter = GeminiAdapter()
        elif self.preferred_llm == "bedrock":
            self.bedrock_adapter = BedrockLlamaAdapter()
        else:
            raise ValueError(f"Unsupported LLM provider: {preferred_llm}")
        
        # Conversation flow steps
        self.conversation_steps = [
            "greeting",
            "name_collection",
            "email_collection", 
            "destination_collection",
            "departure_location_collection",
            "date_collection",
            "travelers_count_collection",
            "trip_type_collection",
            "budget_collection",
            "preferences_collection",
            "confirmation",
            "booking_confirmation",
            "payment_collection",
            "final_confirmation"
        ]
# TODO: Optimize system prompt to give more info to user in context of local information.        
        self.system_prompt = """You are a friendly and professional travel planning assistant. Your goal is to help users plan their perfect trip by collecting necessary information in a conversational manner.

Key guidelines:
1. Be warm, helpful, and enthusiastic about travel
2. Ask one question at a time to avoid overwhelming the user
3. Provide helpful suggestions and recommendations when appropriate
4. Be patient and understanding if users need to clarify or change information
5. Keep responses concise but informative
6. Always maintain a positive, professional tone
7. If users ask about pricing or availability, explain that you'll check real-time information during booking

You should collect the following information step by step:
- Traveler's name
- Email address
- Destination
- Departure location
- Travel dates (departure and return)
- Number of travelers
- Trip type (round trip or one way)
- Budget preferences
- Any special preferences or requirements

Once you have all information, summarize the trip details and ask for confirmation before proceeding to booking."""
    
    def get_adapter(self):
        """Get the appropriate LLM adapter"""
        if self.preferred_llm == "gemini" and self.gemini_adapter.model:
            return self.gemini_adapter
        elif self.preferred_llm == "bedrock" and self.bedrock_adapter.client:
            return self.bedrock_adapter
        elif self.openai_adapter.client:
            return self.openai_adapter
        elif self.gemini_adapter.model:
            return self.gemini_adapter
        elif self.bedrock_adapter.client:
            return self.bedrock_adapter
        else:
            return None
    
    def generate_response(self, user_message: str, conversation_history: list, current_step: str, collected_data: dict) -> tuple:
        """Generate bot response and determine next step"""
        adapter = self.get_adapter()
        if not adapter:
            return "I'm sorry, but I'm currently unable to assist you. Please try again later.", current_step
        
        # Create context-aware prompt based on current step and collected data
        context_prompt = self._build_context_prompt(current_step, collected_data, user_message)
        
        # Generate response
        messages = conversation_history + [{"role": "user", "content": user_message}]
        response = adapter.generate_response(messages, context_prompt)
        
        # Determine next step based on current step and user input
        next_step = self._determine_next_step(current_step, user_message, collected_data)
        
        return response, next_step
    # TODO: Summarize some data, no need for full context.
    def _build_context_prompt(self, current_step: str, collected_data: dict, user_message: str) -> str:
        """Build context-aware prompt for the current conversation step"""
        base_prompt = self.system_prompt
        
        if collected_data:
            data_summary = "Information collected so far:\n"
            for key, value in collected_data.items():
                if value:
                    data_summary += f"- {key.replace('_', ' ').title()}: {value}\n"
            base_prompt += f"\n\n{data_summary}"
        
        step_prompts = {
            "greeting": "Start with a warm greeting and ask for the user's name.",
            "name_collection": "The user should provide their name. Acknowledge it warmly and ask for their email address.",
            "email_collection": "Collect the user's email address. Validate it seems reasonable and ask about their dream destination.",
            "destination_collection": "Ask about their travel destination. Be enthusiastic and ask for departure location.",
            "departure_location_collection": "Ask where they'll be departing from (city/airport).",
            "date_collection": "Ask about their preferred travel dates (departure and return dates).",
            "travelers_count_collection": "Ask how many people will be traveling.",
            "trip_type_collection": "Ask if this is a round trip or one-way journey.",
            "budget_collection": "Ask about their budget range for the trip.",
            "preferences_collection": "Ask about any special preferences, requirements, or activities they're interested in.",
            "confirmation": "Summarize all collected information and ask for confirmation before proceeding to booking.",
            "booking_confirmation": "Confirm they want to proceed with booking and explain the next steps.",
            "payment_collection": "Explain the payment process and ask for confirmation to proceed.",
            "final_confirmation": "Provide final booking confirmation and next steps."
        }
        
        if current_step in step_prompts:
            base_prompt += f"\n\nCurrent step: {step_prompts[current_step]}"
        
        return base_prompt
    
    def _determine_next_step(self, current_step: str, user_message: str, collected_data: dict) -> str:
        """Determine the next conversation step based on current state and user input"""
        current_index = self.conversation_steps.index(current_step) if current_step in self.conversation_steps else 0
        
        # Simple logic to advance steps - can be made more sophisticated
        if current_step == "greeting" and any(word in user_message.lower() for word in ["hi", "hello", "hey", "start"]):
            return "name_collection"
        elif current_step == "name_collection" and len(user_message.strip()) > 0:
            return "email_collection"
        elif current_step == "email_collection" and "@" in user_message:
            return "destination_collection"
        elif current_step == "destination_collection" and len(user_message.strip()) > 0:
            return "departure_location_collection"
        elif current_step == "departure_location_collection" and len(user_message.strip()) > 0:
            return "date_collection"
        elif current_step == "date_collection" and len(user_message.strip()) > 0:
            return "travelers_count_collection"
        elif current_step == "travelers_count_collection" and any(char.isdigit() for char in user_message):
            return "trip_type_collection"
        elif current_step == "trip_type_collection" and len(user_message.strip()) > 0:
            return "budget_collection"
        elif current_step == "budget_collection" and len(user_message.strip()) > 0:
            return "preferences_collection"
        elif current_step == "preferences_collection" and len(user_message.strip()) > 0:
            return "confirmation"
        elif current_step == "confirmation" and any(word in user_message.lower() for word in ["yes", "confirm", "looks good", "correct"]):
            return "booking_confirmation"
        elif current_step == "booking_confirmation" and any(word in user_message.lower() for word in ["yes", "book", "proceed"]):
            return "payment_collection"
        elif current_step == "payment_collection" and any(word in user_message.lower() for word in ["yes", "pay", "proceed"]):
            return "final_confirmation"
        
        # Stay on current step if conditions not met
        return current_step
