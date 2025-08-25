"""
Trip Planner Bot module for handling conversation flow and response generation.
"""
import os
import json
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime
from sqlalchemy import false, true

# Import adapters and constants
from llm_adapters import (
    BedrockLlamaAdapter,
    BedrockLlamaResponseParser,
    BedrockLangChainLlamaAdapter,
    BOT_TEXT_RESPONSE_KEY,
    QUESTION_KEY,
    USER_DATA_KEY,
    TOOL_CALL_KEY,
    TOOL_PARAMETERS_KEY
)
from mcp_travel.mcp_utils import parseDate

logger = logging.getLogger(__name__)

class TripPlannerBot:
    """Main trip planner bot with conversation management"""
    
    def __init__(self, preferred_llm: str = "bedrock"):
        self.preferred_llm = preferred_llm.lower()
        self.openai_adapter = None
        self.gemini_adapter = None
        self.bedrock_adapter = None
        self.bedrock_lang_chain_adapter = None
        
        # Initialize only the requested adapter
        if self.preferred_llm == "bedrock":
            self.bedrock_adapter = BedrockLlamaAdapter()
            self.response_parser = BedrockLlamaResponseParser()
        elif self.preferred_llm == "bedrock_chain":
            self.bedrock_lang_chain_adapter = BedrockLangChainLlamaAdapter()
        else:
            raise ValueError(f"Unsupported LLM provider: {preferred_llm}")
        
        # Conversation flow steps
        self.conversation_steps = [
            "greeting",
            "flight_search",
            "name_collection",
            "email_collection"
            # "booking_confirmation",
            # "payment_collection",
            # "final_confirmation"
        ]
        # Load prompts from files
        self.prompts_dir = os.path.join(os.path.dirname(__file__), "prompts")
        self.system_prompt = self._load_prompt("system_prompt.txt")
        self.step_prompts = {
            step: self._load_prompt(f"{step}.txt")
            for step in self.conversation_steps
        }
        self.guideLines = self._load_prompt("guardContent.txt")
        self.bot_response_format = self._load_prompt("bot_response_format.txt")
        self.result_format = {
            BOT_TEXT_RESPONSE_KEY: "",
            QUESTION_KEY: "",
            USER_DATA_KEY: "",
            TOOL_CALL_KEY: "",
            TOOL_PARAMETERS_KEY: []
        }

    def _load_prompt(self, filename: str) -> str:
        """Load a prompt from a file in the prompts directory."""
        try:
            filepath = os.path.join(self.prompts_dir, filename)
            with open(filepath, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error loading prompt {filename}: {str(e)}")
            return ""

    def get_adapter(self):
        """Get the appropriate LLM adapter"""
        if self.preferred_llm == "bedrock":
            return self.bedrock_adapter
        elif self.preferred_llm == "gemini":
            return self.gemini_adapter
        elif self.preferred_llm == "openai":
            return self.openai_adapter
        elif self.preferred_llm == "bedrock_chain":
            return self.bedrock_lang_chain_adapter
        else:
            raise ValueError(f"Unsupported LLM provider: {self.preferred_llm}")

    def generate_response(self, user_message: str, conversation_history: list, current_step: str, collected_data: dict, booking_service=None):
        """Generate bot response and determine next step"""
        adapter = self.get_adapter()
        
        # Prepare messages for the LLM
        messages = []
        
        # Add conversation history
        # TODO: Sent collected data to conversation history, to later optimize on tokens.
        if conversation_history:
            messages += self._format_conversation_history(conversation_history,collected_data)
        # Add the current user message
        messages.append({"role": "user", "content": user_message})
        
        # Build the context-aware prompt
        context_prompt = self._build_context_prompt(current_step, collected_data, messages)
        bot_response_format = self._build_bot_response_format(self.result_format, collected_data, messages)
        
        # build adapter specific prompt
        adapter_system_prompt = adapter.build_system_prompt(context_prompt, self.guideLines, bot_response_format)
        logger.debug(f"calling generate with following prompt {adapter_system_prompt} and message {messages}")
        # Get response from the LLM with tool support
        response = adapter.generate_response(messages, adapter_system_prompt)
        logger.debug(f"Response from LLM: {response}")
        # Extract response elements
        response_elements = self.extract_response_elements(response)
        logger.debug(f"Response elements: {response_elements}")
        
        # Update collected data if any new data is provided in the response
        if USER_DATA_KEY in response_elements and response_elements[USER_DATA_KEY]:
            self.update_collected_data(collected_data, response_elements[USER_DATA_KEY])
        
        # Determine next step
        next_step = self._determine_next_step(current_step, response_elements.get(BOT_TEXT_RESPONSE_KEY, ""), collected_data)
        
        return response_elements, next_step, collected_data

    def extract_response_elements(self, response_dict):
        """
        Extracts text responses, questions, and tool calls from the response dict.
        Returns a dict with keys: 'message', 'UserData', 'question', 'tool_call', and 'parameters'.
        """
        # If the response is already in the expected format, return it as is
        if all(key in response_dict for key in [BOT_TEXT_RESPONSE_KEY, USER_DATA_KEY, QUESTION_KEY]):
            return response_dict
            
        # Otherwise, parse the response using the BedrockLlamaResponseParser
        parsed_response = self.response_parser.parse_response(response_dict)
        
        # Ensure all required keys are present in the result
        result = self.result_format.copy()
        for key in result:
            if key in parsed_response:
                result[key] = parsed_response[key]
                
        return result

    def _build_bot_response_format(self, result_format: dict, collected_data: dict, messages: list) -> str:
        """
        Merge the default result format with any collected data.
        
        Args:
            result_format: The default response format structure
            collected_data: Any data collected so far in the conversation
            
        Returns:
            str: JSON string representing the merged format
        """
        # Create a deep copy to avoid modifying the original
        logger.debug(f"Building bot response format with collected data: {collected_data}")
        merged = result_format.copy()
        merged[USER_DATA_KEY] = collected_data
        logger.debug(f"Merged bot response format: {merged}")

        bot_format_preamble = f"Respond in JSON and fill {USER_DATA_KEY}\n\n"
        bot_format_preamble += json.dumps(merged, indent=2)
        return bot_format_preamble
        
    def _format_conversation_history(self, conversation_history: list, collected_data: dict) -> list:
        """
        Format conversation history into message dictionaries with appropriate roles.
        If a message has a defined role, use it. Otherwise, alternate between user and assistant.
        For assistant messages in JSON format, extract the question if available.
        
        Args:
            conversation_history: List of message strings or dictionaries in chronological order
            collected_data: Dictionary of collected user data
            
        Returns:
            list: List of message dictionaries with 'role' and 'content' keys
        """
        formatted_messages = []
        
        for i, msg in enumerate(conversation_history):
            # If message is a dictionary with a defined role, use it
            if isinstance(msg, dict) and 'role' in msg:
                role = msg['role']
                content = msg.get('content', '')
                
                # For assistant messages, validate and process content
                if role == 'assistant':
                    try:
                        content_json = None
                        # If content is a string, try to parse it as JSON
                        if isinstance(content, str):
                            try:
                                content_json = json.loads(content)
                            except json.JSONDecodeError:
                                pass  # Not JSON, keep as string
                        
                        # If content is a dict (or was parsed from JSON), try to extract question
                        if isinstance(content_json, dict):
                            question = content_json.get(QUESTION_KEY)
                            if question:
                                content = question
                            elif content_json.get(BOT_TEXT_RESPONSE_KEY):
                                content = content_json.get(BOT_TEXT_RESPONSE_KEY)
                    except Exception as e:
                        logger.warning(f"Error processing assistant message content: {e}")
                # For non-assistant messages or if content isn't a string, ensure proper serialization
                elif not isinstance(content, str):
                    try:
                        content = json.dumps(content)
                    except (TypeError, ValueError) as e:
                        logger.warning(f"Failed to serialize message content: {e}")
                        content = str(content)
                    
                formatted_messages.append({
                    'role': role,
                    'content': content
                })
                
        return formatted_messages

    def _build_context_prompt(self, current_step: str, collected_data: dict, messages: list) -> str:
        base_prompt = self.system_prompt
        # if collected_data:
        #     # data_summary = "Information collected so far:\n"
        #     # for key, value in collected_data.items():
        #     #     if value:
        #     #         data_summary += f"- {key.replace('_', ' ').title()}: {value}\n"
        #     # base_prompt += f"\n\n{data_summary}"
        base_prompt += self.determine_next_action_prompt(collected_data, messages)
        return base_prompt

    def isGreetingPrompt(self, collected_data: dict, messages: list) -> bool:
        """
        Check if the greeting prompt should be used.
        
        Args:
            collected_data: Dictionary containing collected user data
            messages: List of message dictionaries with 'role' and 'content' keys
            
        Returns:
            bool: True if greeting prompt should be used.
        """
        #TODO: Have a counter in collected data, instead of time stamp. Evaluate that. 
        if len(messages) < 2:
            if messages[0]['role'] == 'user' and len(messages[0]['content'].split()) < 4:
                return True
            # message has more than 4 words? possibly a quick instruction. User is a bit terse. 
            return False
        # Check if all non-timestamp keys are empty
        for key, value in collected_data.items():
            if key != 'timestamp' and value:
                # Found a non-empty value in a non-timestamp field
                return False
        return len(messages) < 2

    def determine_next_action_prompt(self, collected_data: dict, messages: list) -> str:
        """
        Determine the next action prompt based on collected data and messages.
        
        Args:
            collected_data: Dictionary containing all collected user data
            messages: List of message dictionaries with 'role' and 'content' keys
            
        Returns:
            str: The prompt string to guide the next action
        """
        # Handle first message case or when no data is collected yet (except timestamp)
        if self.isGreetingPrompt(collected_data, messages):
            return self.step_prompts.get('greeting', '')
        # Check if we have all required information for flight search
        if not self._is_flight_search_info_available(collected_data):
            return self.step_prompts.get('flight_search', '')
        return ""
    
    def _is_flight_search_info_available(self, collected_data: dict) -> bool:
        """
        Check if all required information for flight search is available.
        
        Args:
            collected_data: Dictionary containing collected user data
            
        Returns:
            bool: True if all required flight search fields are present and non-empty, False otherwise
        """
        #TODO: Manage return journey ?
        required_fields = ['destination', 'departure_location', 'travel_dates']
        return all(collected_data.get(field, '').strip() for field in required_fields)

    def update_collected_data(self, collected_data: dict, updated_data: dict) -> None:
        """
        Update the collected data with new values from updated_data.
        Always updates the timestamp if present in updated_data.
        For other fields, only updates if the current value is None or an empty string.
        
        Args:
            collected_data: The main dictionary containing collected user data
            updated_data: Dictionary containing new data to merge in
        """
        if not updated_data:
            return
            
        for key, value in updated_data.items():
            # Skip None values
            if value is None:
                continue
                
            # Strip string values and check if they're empty
            if isinstance(value, str):
                value = value.strip()
                if not value:  # Skip empty strings after stripping
                    continue
            # For non-string values, just check they're not None (already handled)
            # Always update if the key doesn't exist or if the current value is empty/None
            if key not in collected_data or not collected_data[key]: 
                if 'date' in key.lower():
                    # Handle date field
                    #TODO: Set up observer on collected_data
                    collected_data[key] = parseDate(value)
                else:
                    collected_data[key] = value
            # Special handling for timestamp - always update to current one.
            if key == 'timestamp':
                collected_data[key] = datetime.now().isoformat()
            

    def _determine_next_step(self, current_step: str, user_message: str, collected_data: dict) -> str:
        """Determine the next conversation step based on current state and user input"""
        # This is a simplified implementation. You can expand this based on your state machine logic.
        if not current_step or current_step not in self.conversation_steps:
            return self.conversation_steps[0]  # Start from the beginning
            
        current_index = self.conversation_steps.index(current_step)
        # if(_is_flight_search_result_available(collected_data)):
        #     return self.conversation_steps[current_index + 1]
        
        # Basic logic: move to next step unless we're at the end
        if current_index < len(self.conversation_steps) - 1:
            return self.conversation_steps[current_index + 1]
        return current_step  # Stay on the last step if we've reached the end


def main():
    """Run the TripBot in command line mode"""
    import asyncio
   
    
    # Set up logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Initialize the bot
    print("Welcome to TripBot! Type 'quit' to exit.")
    bot = TripPlannerBot(preferred_llm="bedrock")
    
 # Initialize conversation state
    conversation_history = []
    current_step = "greeting"
    collected_data = {
        'timestamp': datetime.now().isoformat(),
        'UserName': "",
        'email': "",
        'destination': "",
        'departure_location': "",
        'dates': "",
        'travelers_count': "",
        'trip_type': "",
        'budget': "",
        'preferences': {}
    }
    
    try:
        
        # Main conversation loop
        while True:
            # Get user input
            user_input = input("\nYou: ")
            if user_input.lower() in ['quit', 'exit', 'bye']:
                print("Goodbye!")
                break
                
            # Generate bot response
            bot_response, next_step, updated_data = bot.generate_response(
                user_message=user_input,
                conversation_history=conversation_history,
                current_step=current_step,
                collected_data=collected_data
            )
            logger.debug(f"Next Step: {next_step}")
            logger.debug(f"Response:\n{json.dumps(bot_response, indent=2, default=str)}")
            logger.debug(f"Updated Data:\n{json.dumps(updated_data, indent=2, default=str)}")
            # Update conversation state with custom merge that preserves non-empty values
            current_step = next_step
            bot.update_collected_data(collected_data, updated_data or {})
            
            # Update conversation history
            conversation_history.append({'role': 'user', 'content': user_input})
            conversation_history.append({'role': 'assistant', 'content': json.dumps(bot_response)})

            current_step = next_step
            bot.update_collected_data(collected_data, updated_data)
            
            # Print bot response
            print(f"\nBot: {bot_response[BOT_TEXT_RESPONSE_KEY]}")
            if bot_response.get(QUESTION_KEY):
                print(f"Question: {bot_response[QUESTION_KEY]}")
                
    except KeyboardInterrupt:
        print("\nExiting...")
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
