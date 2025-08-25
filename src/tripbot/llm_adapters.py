import os
import json
import logging
import time
import traceback
from typing import Any, Dict, List, Optional, Iterator, Mapping, Union
from datetime import datetime
from pydantic import Json

import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from typing import Final

# Response dictionary keys
# TODO: Eventually create a new package and move these constants and dataformat there.
# CAUTION: Check prompts language before changing these constants and values.
BOT_TEXT_RESPONSE_KEY: Final[str] = "response"
QUESTION_KEY: Final[str] = "question"
USER_DATA_KEY: Final[str] = "UserData"
TOOL_CALL_KEY: Final[str] = "tool_call"
TOOL_PARAMETERS_KEY: Final[str] = "parameters"

# Import logging configuration
from tripbot.config.logging_config import setup_logging

# Initialize logging
setup_logging()
logger = logging.getLogger(__name__)

class LLMAdapter:
    """Base class for LLM adapters"""
    
    def generate_response(self, messages: list, system_prompt: Any = None) -> dict:
        """Generate a response from the LLM"""
        raise NotImplementedError

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
        logging.getLogger('botocore').setLevel(logging.ERROR)
        logging.getLogger('boto3').setLevel(logging.ERROR)
        logging.getLogger('urllib3').setLevel(logging.ERROR)

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
    
    def generate_response(self, messages: list, system_prompt: Any = None) -> dict:
        """Generate response using AWS Bedrock Llama models"""    
        try:
            # Log the incoming request
            logger.debug(f"Generating response with system prompt: {system_prompt}")
            logger.debug(f"Messages: {json.dumps(messages, indent=2)}")
            
            # Convert messages to Llama format
            conversation_text = []
            # if system_prompt:
            #     conversation_text += f"System: {system_prompt}\n\n"
            
            for message in messages:
                if message["role"] == "user" :
                    conversation_text.append({"role": "user", "content": [{"text":message['content']}]})
                elif message["role"] == "Assistant":
                    conversation_text.append({"role": "Assistant","content": [{"text":message['content']}]})
                
            # Get model ID from environment variable or use default
            model_id = os.environ.get('AWS_MODEL_ID', 'meta.llama3-70b-instruct-v1:0')
            logger.debug(f"Using model ID: {model_id}")    
            try:
                # Add timeout to the request
                request_config = {
                    'modelId': model_id,
                    'messages': conversation_text,
                    'system': system_prompt
                }
                
                # Get a fresh client for this request
                client = self._get_client()
                if not client:
                     return {BOT_TEXT_RESPONSE_KEY: "I'm having trouble connecting to the AI service. Please try again later."}
                
                # Log the request with timing
                start_time = time.time()
                try:
                    response =  client.converse(**request_config)
                    elapsed = time.time() - start_time
                    logger.debug(f"Received response: {json.dumps(response, indent=2)[:50000]}...")
                    logger.debug(f"Bedrock API call completed in {elapsed:.2f} seconds")
                    if elapsed > 10:  # Log warning for slow responses
                        logger.warning(f"Slow Bedrock API response: {elapsed:.2f} seconds")
                except Exception as e:
                    elapsed = time.time() - start_time
                    logger.error(f"Bedrock API call failed after {elapsed:.2f} seconds: {str(e)}")
                    raise               
                return response
        
            except ClientError as e:
                error_code = e.response.get('Error', {}).get('Code', 'Unknown')
                error_message = e.response.get('Error', {}).get('Message', 'No error message')
                logger.error(f"AWS Bedrock API error - Code: {error_code}, Message: {error_message}")

                if error_code == 'AccessDeniedException':
                    return {BOT_TEXT_RESPONSE_KEY: "I don't have permission to access the language model. Please check your AWS permissions."}
                elif error_code == 'ResourceNotFoundException':
                    return {BOT_TEXT_RESPONSE_KEY: "The requested language model was not found. Please check the model ID."}
                elif error_code == 'ThrottlingException':
                    return {BOT_TEXT_RESPONSE_KEY: "The service is currently experiencing high traffic. Please try again in a moment."}
                else:
                    return {BOT_TEXT_RESPONSE_KEY: f"I encountered an error with the language model: {error_message}"}
    
        except Exception as e:
                error_type = type(e).__name__
                error_message = str(e)
                logger.critical(
                    f"Unexpected error in generate_response: {error_type}: {error_message}\n"
                    f"Full traceback:\n{traceback.format_exc()}"
                )
                return {BOT_TEXT_RESPONSE_KEY: "I apologize, but I'm experiencing some technical difficulties. Please try again in a moment."}

        
    def build_system_prompt(self, system_prompt, guideLines=None, bot_response_format=None, cachePoint=None):
        #return [{"role": 'text', "content": [{"text":system_prompt}]}]
        result = []
        if not system_prompt:  # Checks for None, empty string, or falsy value
            raise ValueError("system_prompt is required and cannot be empty")
        result.append({"text": system_prompt})
        if guideLines:
            result.append({"text": guideLines})
        if bot_response_format:
            result.append({"text": bot_response_format})
        if cachePoint:
            result.append({"cachePoint": cachePoint})
        return result

from langchain_core.callbacks.manager import CallbackManagerForLLMRun
from langchain_core.outputs import GenerationChunk
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from langchain_core.load import dumps
from langchain_core.runnables import RunnableSequence
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

class BedrockLangChainLlamaAdapter(LLMAdapter):
    """LangChain style adapter for AWS Bedrock's Llama models with | operator support."""

    def __init__(self, model_id: str = "meta.llama3-70b-instruct-v1:0", temperature: float = 0.7):
        self.model_id = model_id
        self.temperature = temperature
        self.client = None
        logger.info(f"Initialized BedrockLangChainLlamaAdapter with model: {model_id}")
    
    def _get_client(self):
        """Get or create a Bedrock client."""
        logging.getLogger('botocore').setLevel(logging.DEBUG)
        logging.getLogger('boto3').setLevel(logging.ERROR)
        logging.getLogger('urllib3').setLevel(logging.ERROR)
        if self.client is None:
            try:
                session = boto3.Session()
                self.client = session.client('bedrock-runtime')
            except Exception as e:
                logger.error(f"Error creating Bedrock client: {str(e)}")
                raise
        return self.client
    
    def build_system_prompt(self, system_prompt: str, guidelines: Optional[str] = None, 
                          response_format: Optional[dict] = None) -> Any:
        """Build a system prompt with optional guidelines and response format."""
        prompt_parts = [system_prompt]
        
        if guidelines:
            prompt_parts.append(f"\nGuidelines:\n{guidelines}")
            
        if response_format:
            format_str = json.dumps(response_format, indent=2)
            prompt_parts.append(f"Respond ONLY in JSON.Fill UserData if avaialble in JSON.\n{format_str}")
            
        return "\n".join(prompt_parts)
    
    def generate_response(self, messages: List[Dict[str, Any]], system_prompt: Any = None, 
                        output_parser: Optional[Any] = None, return_raw: bool = False):
        """
        Generate response using AWS Bedrock Llama models with raw response access.
        
        Args:
            messages: List of message dictionaries with 'role' and 'content' keys
            system_prompt: Optional system prompt or list of system messages
            output_parser: Optional output parser to process the response
            return_raw: If True, returns the raw response object with metadata
            
        Returns:
            dict: Response containing text and metadata if return_raw=True,
                  otherwise returns formatted response
        """
        try:
            # Convert messages to LangChain format
            langchain_messages = []
            
            # Add system prompt if provided
            if system_prompt:
                if isinstance(system_prompt, (str, dict)):
                    langchain_messages.append(SystemMessage(content=system_prompt))
                elif isinstance(system_prompt, list):
                    for item in system_prompt:
                        if isinstance(item, dict) and 'text' in item:
                            langchain_messages.append(SystemMessage(content=item['text']))
            
            # Add conversation messages
            for msg in messages:
                role = msg.get('role', '').lower()
                content = msg.get('content', '')
                
                if role == 'user':
                    langchain_messages.append(HumanMessage(content=content))
                elif role == 'assistant':
                    langchain_messages.append(AIMessage(content=content))
                elif role == 'tool':
                    langchain_messages.append(ToolMessage(
                        content=content, 
                        tool_call_id=msg.get('tool_call_id', '')
                    ))
            
            # Create prompt and chain
            prompt = ChatPromptTemplate.from_messages(langchain_messages)
            logger.debug(f"Going ahead with prompt:\n{dumps(prompt, pretty=True)}")
            
            # Create the LLM with callback for raw response
            from langchain_core.callbacks.base import BaseCallbackHandler
            
            class RawResponseCallback(BaseCallbackHandler):
                def __init__(self):
                    super().__init__()
                    self.raw_response = None
                    self.metadata = {}
                
                def on_llm_end(self, response, **kwargs):
                    self.raw_response = response
                    logger.debug(f"Raw response: {json.dumps(response, indent=2)[:50000]}")
                    self.metadata.update({
                        'model_name': getattr(response, 'model_name', None),
                        'token_usage': getattr(response, 'usage', {})
                    })
            
            # Initialize callback
            callback = RawResponseCallback()
            
            # Configure the LLM with our callback
            llm = self._create_langchain_llm().with_config({
                'callbacks': [callback]
            })
            
            # Create and invoke the chain
            chain = prompt | llm
            if output_parser:
                chain = chain | output_parser
            else:
                from langchain_core.output_parsers import StrOutputParser
                chain = chain | StrOutputParser()
            
            start_time = time.time()
            response = chain.invoke({})
            elapsed = time.time() - start_time
            logger.debug(f"LLM processing completed in {elapsed:.2f} seconds")
            
            # Return raw response if requested
            if return_raw:
                return {
                    'raw_response': callback.raw_response,
                    'metadata': {
                        **callback.metadata,
                        'processing_time_seconds': elapsed,
                        'model_id': self.model_id,
                        'temperature': self.temperature
                    },
                    'parsed_response': response if output_parser else None
                }
            
            # Return parsed response if parser provided
            if output_parser:
                return response
                
            # Default return format
            return {
                BOT_TEXT_RESPONSE_KEY: response,
                USER_DATA_KEY: {},
                QUESTION_KEY: None,
                'metadata': {
                    'processing_time_seconds': elapsed,
                    'model_id': self.model_id
                }
            }
            
        except Exception as e:
            logger.error(f"Error in generate_response: {str(e)}", exc_info=True)
            return {
                BOT_TEXT_RESPONSE_KEY: f"I encountered an error: {str(e)}",
                USER_DATA_KEY: {},
                QUESTION_KEY: None,
                'error': str(e),
                'traceback': traceback.format_exc()
            }
    
    def _create_langchain_llm(self):
        """Create a LangChain compatible LLM instance."""
        from langchain_aws import BedrockLLM
        
        return BedrockLLM(
            model_id=self.model_id,
            client=self._get_client(),
            model_kwargs={
                'temperature': self.temperature,
                'max_tokens':2048,
                'top_p': 0.9,
            },
            streaming=False
        )
    
    def __or__(self, other):
        """Enable the | operator for chaining with other LangChain components."""
        if isinstance(other, (ChatPromptTemplate, PromptTemplate)):
            return RunnableSequence(other, self._create_langchain_llm())
        return NotImplemented

from langchain_core.output_parsers import BaseOutputParser
from typing import TypeVar, Any, Dict

class BedrockLlamaResponseParser(BaseOutputParser[Dict[str, Any]]):
    """Class responsible for parsing responses from AWS Bedrock Llama models"""
    
    @property
    def _type(self) -> str:
        return "bedrock_llama_response_parser"

    async def aparse(self, text: str) -> Dict[str, Any]:
        import anyio
        return await anyio.to_thread(self.parse, text)
    
    def parse(self, text: str) -> Dict[str, Any]:
        return self.parse_response(text)

    def extract_bot_format_from_json(self, text):
        """
        Extract and process bot response in the expected format.
        
        Args:
            text: The text content to parse (expected to be JSON string)
            
        Returns:
            dict or None: Parsed result dictionary if successful, None otherwise
        """
        try:
            parsed = json.loads(text)
            self.logger.debug(f'Parsed response: {json.dumps(parsed, indent=2)[:50000]}')
            result = {}         
            # Handle message from parsed JSON
            if BOT_TEXT_RESPONSE_KEY in parsed:
                result[BOT_TEXT_RESPONSE_KEY] = parsed.get(BOT_TEXT_RESPONSE_KEY, '')      
            # Handle UserData
            if USER_DATA_KEY in parsed:
                result[USER_DATA_KEY] = parsed.get(USER_DATA_KEY, {})               
            # Handle question extraction
            if QUESTION_KEY in parsed:
                result[QUESTION_KEY] = parsed.get(QUESTION_KEY, '')
                # Check for questions if question is not in the format
                if not result[QUESTION_KEY] and BOT_TEXT_RESPONSE_KEY in result and any(
                    marker in result[BOT_TEXT_RESPONSE_KEY].lower() 
                    for marker in ['?', 'could you', 'would you', 'can you', 'please tell', 'what is', 'when is', 'where is']
                ):
                    result[QUESTION_KEY] = result[BOT_TEXT_RESPONSE_KEY]
                    result[BOT_TEXT_RESPONSE_KEY] = None
            
            self.logger.debug(f'extracted result from json: {json.dumps(result, indent=2)[:50000]}')
            return result if any(result.values()) else None
            
        except json.JSONDecodeError as e:
            self.logger.debug(f"JSON decode error in extractBotFormat: {str(e)}")
            return None
    
    def extract_bot_fromat_from_Text(self, text: str) -> dict:
        """
        Extract and process structured data from the LLM response.
        
        Args:
            text: The raw text from the LLM response
            
        Returns:
            dict: A dictionary containing parsed response components including:
                  - message: The main response message
                  - UserData: Extracted user data as a dictionary
                  - question: Any follow-up question if present
        """
        try:
            # Find the first occurrence of '{' and last occurrence of '}'
            start = text.find('{')
            end = text.rfind('}')
            
            if start == -1 or end == -1 or start >= end:
                # If no JSON object found, return the text as is
                return {BOT_TEXT_RESPONSE_KEY: text}
                
            # Extract the JSON string
            json_str = text[start:end+1]
            logger.debug(f"Extracted String is {json_str}")
            # Parse the JSON string
            result = json.loads(json_str)
            # capture line before { and append to result[BOT_TEXT_RESPONSE_KEY]
            if(result[BOT_TEXT_RESPONSE_KEY]):
                if(text[0:start-1]):
                    result[BOT_TEXT_RESPONSE_KEY] = text[0:start-1] + result[BOT_TEXT_RESPONSE_KEY]
 
            # Ensure the result is a dictionary
            if not isinstance(result, dict):
                return {BOT_TEXT_RESPONSE_KEY: text}
                
            # Ensure the required keys exist in the result
            if BOT_TEXT_RESPONSE_KEY not in result:
                result[BOT_TEXT_RESPONSE_KEY] = text
            
            return result
            
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON from response: {e}")
            return {BOT_TEXT_RESPONSE_KEY: text}
        except Exception as e:
            logger.error(f"Unexpected error parsing response: {e}")
            return {BOT_TEXT_RESPONSE_KEY: text}
    
    def parse_response(self, response) -> dict:
        """
        Parse the LLM response and return a dictionary with the text response.
        
        Args:
            response: Raw response from LLM API
            
        Returns:
            dict: Contains 'message' and 'data' keys from the response
        """
        logger.debug(f'Model Latency in ms: {response["metrics"]["latencyMs"]}')
        logger.debug(f'Response stop reason {response["stopReason"]}')
        logger.debug(f'Usage metrics total tokens: {response["usage"]["totalTokens"]}')
        logger.debug(f'Usage metrics input tokens: {response["usage"].get("inputTokens")}')
        logger.debug(f'Usage metrics output tokens: {response["usage"].get("outputTokens")}')
        
        result = {}
        
        if isinstance(response, dict):
            output_message = response.get('output', {}).get('message', {})
            for content_block in output_message.get('content', []):
                if 'text' in content_block and content_block['text']:
                    try:
                        # Try to parse as JSON
                        text = content_block['text'].strip()
                        if text.startswith('{') and text.endswith('}'):
                            parsed_result = self.extract_bot_format_from_json(text)
                            if parsed_result:
                                result.update(parsed_result)
                                continue  # Successfully parsed, no need to process further
                        # If not in bot format, try to extract as plain text
                        text_parsed_results = self.extract_bot_fromat_from_Text(content_block['text'])
                        if text_parsed_results:
                            result.update(text_parsed_results)
                            continue
                        # Text did not have the prescribed format    
                        # Check if the text contains a question
                        # TODO: Move this phrases into templates and eventually language specific templates.
                        if any(marker in text.lower() for marker in ['?', 'could you', 'would you', 'can you', 'please tell', 'what is', 'when is', 'where is']):
                            result[QUESTION_KEY] = text
                        else:
                            result[BOT_TEXT_RESPONSE_KEY] = text
                    except json.JSONDecodeError as e:
                        self.logger.debug(f"Json Decode error {str(e)}")
                        result[BOT_TEXT_RESPONSE_KEY] = text

                if TOOL_CALL_KEY in content_block and content_block[TOOL_CALL_KEY]:
                    result[TOOL_CALL_KEY] = content_block[TOOL_CALL_KEY]
                if 'parameters' in content_block and content_block['parameters']:
                    result["parameters"] = content_block['parameters']
        
        return result


__all__ = ['LLMAdapter', 'BedrockLlamaAdapter', 'BedrockLangChainLlamaAdapter', 
           'BedrockLlamaResponseParser', 'BOT_TEXT_RESPONSE_KEY', 'QUESTION_KEY', 'USER_DATA_KEY', 'TOOL_CALL_KEY',TOOL_PARAMETERS_KEY]
