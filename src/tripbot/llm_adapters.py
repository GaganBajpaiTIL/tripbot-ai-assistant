import os
import json
import logging
import time
import traceback
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
            chat_messages = []
            
            if system_prompt:
                chat_messages.append({"role": "system", "content": system_prompt})
            
            chat_messages.extend(messages)
            
            # Define flight search tool
            flight_search_tools = [{
                "type": "function",
                "function": {
                    "name": "search_flights",
                    "description": "Search for available flights based on the given parameters",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "travel_date": {
                                "type": "string",
                                "description": "Departure date in YYYY-MM-DD format"
                            },
                            "source": {
                                "type": "string",
                                "description": "Source city or airport code (e.g., 'DEL' for Delhi)"
                            },
                            "destination": {
                                "type": "string", 
                                "description": "Destination city or airport code (e.g., 'BOM' for Mumbai)"
                            },
                            "return_date": {
                                "type": "string",
                                "description": "Return date in YYYY-MM-DD format (for round trips)"
                            },
                            "adults": {
                                "type": "integer",
                                "description": "Number of adult passengers"
                            },
                            "children": {
                                "type": "integer",
                                "description": "Number of child passengers"
                            },
                            "travel_class": {
                                "type": "string",
                                "enum": ["ECONOMY", "PREMIUM_ECONOMY", "BUSINESS", "FIRST"],
                                "description": "Travel class"
                            },
                            "max_results": {
                                "type": "integer",
                                "description": "Maximum number of flight results to return (default: 5)"
                            }
                        },
                        "required": ["travel_date", "source", "destination"]
                    }
                }
            }]
            
            # Use provided tools or default to flight search tools
            tools_to_use = tools if tools is not None else flight_search_tools
            
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=chat_messages,
                tools=tools_to_use,
                tool_choice="auto",
                max_tokens=1000,
                temperature=0.7
            )
            
            response_message = response.choices[0].message
            
            # Check if the model wants to call a function
            if hasattr(response_message, 'tool_calls') and response_message.tool_calls:
                return {
                    "tool_calls": response_message.tool_calls,
                    "content": response_message.content
                }
            
            return {"content": response_message.content}
            
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
        # Store configuration but don't create client yet
        self.config = {
            'config': {
                'connect_timeout': 10,  # 10 seconds connection timeout
                'read_timeout': 60,     # 60 seconds read timeout
                'retries': {
                    'max_attempts': 3,  # Retry up to 3 times
                    'mode': 'standard'  # Standard retry mode
                },
                'max_pool_connections': 10  # Limit connection pool size
            }
        }
        logger.info("Bedrock client configuration initialized")
        
    def _get_client(self):
        """Create a new thread-local client instance"""
        # Set up logging
        logging.getLogger('botocore').setLevel(logging.DEBUG)
        logging.getLogger('boto3').setLevel(logging.DEBUG)
        logging.getLogger('urllib3').setLevel(logging.DEBUG)

        try:
            # Create a new session and client for this request
            session = boto3.Session()
            client = session.client('bedrock-runtime')
            return client
        except NoCredentialsError:
            logger.error("AWS credentials not found")
            return None
        except Exception as e:
            logger.error(f"Error creating Bedrock client: {str(e)}")
            return None
    
    def generate_response(self, messages: list, system_prompt: str = None) -> str:
        """Generate response using AWS Bedrock Llama models"""    
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
                # Add timeout to the request
                request_config = {
                    'modelId': model_id,
                    'body': body,
                    'contentType': 'application/json',
                    'accept': 'application/json'
                }
                
                # Get a fresh client for this request
                client = self._get_client()
                if not client:
                    return "I'm having trouble connecting to the AI service. Please try again later."
                
                # Log the request with timing
                start_time = time.time()
                try:
                    response =  client.invoke_model(**request_config)
                    elapsed = time.time() - start_time
                    logger.debug(f"Bedrock API call completed in {elapsed:.2f} seconds")
                    if elapsed > 10:  # Log warning for slow responses
                        logger.warning(f"Slow Bedrock API response: {elapsed:.2f} seconds")
                except Exception as e:
                    elapsed = time.time() - start_time
                    logger.error(f"Bedrock API call failed after {elapsed:.2f} seconds: {str(e)}")
                    raise
                
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
            error_type = type(e).__name__
            error_message = str(e)
            logger.critical(
                f"Unexpected error in generate_response: {error_type}: {error_message}\n"
                f"Full traceback:\n{traceback.format_exc()}"
            )
            return "I apologize, but I'm experiencing some technical difficulties. Please try again in a moment."
        except BaseException as e:  # Catch base exceptions including KeyboardInterrupt, SystemExit, etc.
            error_type = type(e).__name__
            logger.critical(
                f"Critical error in generate_response (BaseException): {error_type}: {str(e)}\n"
                f"Full traceback:\n{traceback.format_exc()}"
            )
            # Re-raise base exceptions to allow proper process termination
            return "I apologize, but I'm experiencing some technical difficulties at network. Please try again in a moment."

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

TOOLS:
- You have access to a flight search tool that can find available flights based on user requirements.
- When a user asks about flight options or availability, use the search_flights tool with the available parameters.
- Always confirm the search parameters with the user before performing the search.
- Present the flight options in a clear, easy-to-read format.

You should collect the following information step by step when helping with flight bookings:
- Departure location (city or airport code)
- Destination (city or airport code)
- Travel dates (departure and return if round trip)
- Number of travelers (adults, children, infants)
- Travel class (Economy, Premium Economy, Business, First)
- Any special preferences (e.g., non-stop flights, specific airlines, etc.)

Once you have the flight options, help the user compare and choose the best option based on their preferences."""
    
    def get_adapter(self):
        """Get the appropriate LLM adapter"""
        if self.preferred_llm == "gemini" and self.gemini_adapter.model:
            return self.gemini_adapter
        elif self.preferred_llm == "bedrock":
            return self.bedrock_adapter
        elif self.openai_adapter.client:
            return self.openai_adapter
        elif self.gemini_adapter.model:
            return self.gemini_adapter
        elif self.bedrock_adapter.client:
            return self.bedrock_adapter
        else:
            return None
    
    def generate_response(self, user_message: str, conversation_history: list, current_step: str, collected_data: dict, booking_service=None):
        """Generate bot response and determine next step"""
        adapter = self.get_adapter()
        if not adapter:
            return "I'm sorry, but I'm having trouble connecting to my language processing service. Please try again later.", current_step, collected_data
        
        # Build the context-aware prompt
        context_prompt = self._build_context_prompt(current_step, collected_data, user_message)
        
        # Prepare conversation history for the LLM
        messages = []
        if conversation_history:
            messages = [
                {"role": "user" if i % 2 == 0 else "assistant", "content": msg}
                for i, msg in enumerate(conversation_history)
            ]
        
        # Add the current user message
        messages.append({"role": "user", "content": user_message})
        
        # Get response from the LLM with tool support
        response = adapter.generate_response(messages, context_prompt)
        
        # Check if there are any tool calls to handle
        if isinstance(response, dict) and 'tool_calls' in response and booking_service:
            tool_calls = response['tool_calls']
            tool_responses = []
            
            for tool_call in tool_calls:
                if tool_call.function.name == "search_flights":
                    try:
                        # Parse the function arguments
                        import json
                        args = json.loads(tool_call.function.arguments)
                        
                        # Call the booking service to search for flights
                        flights = booking_service.search_flights(
                            travel_date=args.get('travel_date'),
                            source=args.get('source'),
                            destination=args.get('destination'),
                            return_date=args.get('return_date'),
                            adults=args.get('adults', 1),
                            children=args.get('children', 0),
                            travel_class=args.get('travel_class', 'ECONOMY'),
                            max_results=args.get('max_results', 5)
                        )
                        
                        # Format the flight results
                        tool_response = {
                            "tool_call_id": tool_call.id,
                            "role": "tool",
                            "name": "search_flights",
                            "content": json.dumps(flights)
                        }
                        tool_responses.append(tool_response)
                        
                    except Exception as e:
                        logger.error(f"Error in flight search: {e}")
                        tool_responses.append({
                            "tool_call_id": tool_call.id,
                            "role": "tool",
                            "name": "search_flights",
                            "content": "Error: Unable to search for flights at the moment. Please try again later."
                        })
            
            # If we have tool responses, send them back to the LLM
            if tool_responses:
                # Add the tool responses to the messages
                for response in tool_responses:
                    messages.append(response)
                
                # Get a new response from the LLM with the tool results
                response = adapter.generate_response(messages, context_prompt)
        
        # If response is a dict (from tool processing), extract the content
        if isinstance(response, dict):
            response = response.get('content', 'I apologize, but I encountered an error processing your request.')
        
        # Determine the next step based on the conversation
        next_step = self._determine_next_step(current_step, user_message, collected_data)
        
        # If we have all required information, move to confirmation
        if next_step == "confirmation" and current_step != "confirmation":
            response = self._build_confirmation_message(collected_data)
            return response, "confirmation", collected_data
        
        return response, next_step, collected_data
    
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
