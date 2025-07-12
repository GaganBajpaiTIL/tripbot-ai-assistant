from doctest import debug
import json
import logging
import os
import sys
from datetime import datetime, timedelta
import random
import time
from typing import Any, Callable, Dict, List, Optional, Literal, Type, TypeVar, Tuple

import isodate
from amadeus import Client, Location, ResponseError

T = TypeVar('T')  # Generic type for the return value of the function being retried

logger = logging.getLogger(__name__)


def call_with_retry(
    func: Callable[..., T],
    max_retries: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    jitter: bool = True,
    **kwargs
) -> T:
    """
    Call a function with retry logic, exponential backoff, and optional jitter.
    Returns the function's result if successful, or raises the last exception if all retries fail.

    Args:
        func: The function to call
        max_retries: Maximum number of retry attempts (default: 3)
        initial_delay: Initial delay between retries in seconds (default: 1.0)
        backoff_factor: Multiplier for the delay between retries (default: 2.0)
        jitter: If True, adds random jitter to the delay (default: True)
        **kwargs: Arguments to pass to the function

    Returns:
        The result of the function call if successful

    Raises:
        Exception: The last exception encountered if all retries fail
    """
    
    # Log function call with parameter count and names (but not values for security)
    param_count = len(signature(func).parameters)
    logger.debug(f"Calling {func.__name__} with {param_count} parameters: {list(kwargs.keys())}")
    
    delay = initial_delay
    last_exception = None

    for attempt in range(max_retries + 1):
        try:
            return func(**kwargs)
        except ResponseError as e:
            last_exception = e
            if attempt == max_retries:
                logger.error(f"API call failed after {max_retries} attempts. Last error: {str(e)}")
                break
                
            # Calculate delay with jitter
            current_delay = delay
            if jitter:
                # Add up to 25% jitter to the delay
                jitter_amount = random.uniform(0, delay * 0.25)
                current_delay = delay + jitter_amount
                
            logger.warning(
                f"API call failed (attempt {attempt + 1}/{max_retries}). "
                f"Retrying in {current_delay:.1f} seconds. Error: {str(e)}"
            )
            time.sleep(current_delay)
            delay *= backoff_factor
        except Exception as e:
            last_exception = e
            logger.error(f"Unexpected error in API call: {str(e)}")
            break

    # If we get here, all retries failed
    raise last_exception


def print_sys_path(header: str = "sys.path") -> None:
    """Print the current Python path with a header.
    
    Args:
        header: Optional header text to display before the path listing
    """
    print(f"\n=== {header} ===")
    for i, path in enumerate(sys.path, 1):
        print(f"{i}. {path}")
    print()

# Print initial Python path
print_sys_path("Initial sys.path")

# Correctly determine the project root relative to app.py
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

# Add parent directory to path
parent_dir = os.path.join(os.path.dirname(__file__), '..')
sys.path.append(parent_dir)

# Print updated Python path
print_sys_path("Updated sys.path")



def initialize_amadeus() -> Client:
    """
    Initialize and return an authenticated Amadeus client.
    
    Returns:
        Client: Authenticated Amadeus client instance
    """
    amadeus_client = Client(
        client_id=os.getenv('AMADEUS_CLIENT_ID', 'q8z8tQK3xV7zrIhPRd3NrRv3JA0noqI2'),
        client_secret=os.getenv('AMADEUS_CLIENT_SECRET', 'wyAAfcSGJFoM3X5f'),
        log_level="error"
    )
    
    # Verify that credentials are provided
    if not amadeus_client.client_id or not amadeus_client.client_secret:
        raise ValueError(
            'Amadeus API credentials not found. Please set AMADEUS_CLIENT_ID and '
            'AMADEUS_CLIENT_SECRET environment variables.'
        )
    
    # Test the connection
    try:
        response = amadeus_client.reference_data.locations.get(
            keyword='LON',
            subType=Location.AIRPORT
        )
        logger.info("Successfully connected to Amadeus API")
        logger.debug("Amadeus API connection response: %s", response.data)
        return amadeus_client
    except ResponseError as error:
        logger.error(f"Failed to initialize Amadeus client: {error}")
        raise


class FlightSearchMCP:
    """
    A class to handle flight search operations using the Amadeus API.
    
    This class provides methods to search for flights, process the results,
    and sort them based on various criteria.
    """
    
    # Valid travel classes as a module-level constant
    VALID_TRAVEL_CLASSES = ['ECONOMY', 'PREMIUM_ECONOMY', 'BUSINESS', 'FIRST']

    def __init__(self, client: Optional[Client] = None):
        """
        Initialize the FlightSearchMCP with an optional Amadeus client.
        
        Args:
            client: Optional Amadeus client instance. If not provided,
                   a new client will be initialized.
        """
        logger.info("Initializing FlightSearchMCP")
        self.client = client or initialize_amadeus()
        logger.debug("FlightSearchMCP initialized with client: %s", type(self.client).__name__)
    
    @staticmethod
    def sort_by_duration(flight: Dict[str, Any]) -> int:
        """
        Sort flights by duration (shortest first).
        
        Args:
            flight: Flight data dictionary
            
        Returns:
            int: Total duration in minutes for sorting
            
        Note:
            Uses isodate for reliable ISO 8601 duration parsing
        """
        duration_str = flight['itineraries'][0]['duration']
        duration = isodate.parse_duration(duration_str)
        return int(duration.total_seconds() // 60)


    @staticmethod
    def sort_by_price(flight: Dict[str, Any]) -> float:
        """Sort flights by price (cheapest first)."""
        return float(flight['price']['total'])


    def search_flights(
        self,
        travel_date: str = "2025-07-20",
        return_date: Optional[str] = None,
        source: str = "HYD",
        destination: str = "SFO",
        adults: int = 1,
        children: int = 0,
        infants: int = 0,
        travel_class: str = 'ECONOMY',
        max_results: int = int(os.getenv("MAX_SEARCH_RESULTS", 5)),
        include_business_class: bool = True,
        include_premium_economy: bool = True,
        non_stop: bool = False,
        max_price: Optional[float] = None,
        currencyCode: str = "INR",
        sort_func: Callable[[Dict[str, Any]], Any] = sort_by_duration
    ) -> List[Dict[str, Any]]:
        """
        Searches for available flights between a source and destination on a given date.
        
        Args:
            travel_date: The desired date of travel in 'YYYY-MM-DD' format
            return_date: The desired date of return in 'YYYY-MM-DD' format (optional)
            source: The departure airport code (e.g., 'SFO', 'LAX') or city name
            destination: The arrival airport code (e.g., 'JFK', 'LHR') or city name
            adults: Number of adult passengers (1-9)
            children: Number of child passengers (0-8)
            infants: Number of infant passengers (0-5, cannot exceed number of adults)
            travel_class: Travel class ('ECONOMY', 'PREMIUM_ECONOMY', 'BUSINESS', 'FIRST')
            max_results: Maximum number of results to return (1-10)
            include_business_class: Whether to include business class flights
            include_premium_economy: Whether to include premium economy flights
            non_stop: Whether to include only non-stop flights
            max_price: Maximum price for the flight (in the specified currency)
            currency_code: Currency code for pricing (3-letter ISO code, e.g., 'USD', 'EUR', 'INR')
            sort_func: Function to use for sorting results
            
        Returns:
            List of flight options matching the search criteria
            
        Raises:
            ValueError: If any of the input parameters are invalid
            ResponseError: If there's an error with the Amadeus API request
        """

        # Validate parameters
        self._validate_airport_code(source, "origin")
        self._validate_airport_code(destination, "destination")
            
        self._validate_passenger_count(adults, children, infants)
        self._validate_travel_class(travel_class)
        
        validate_currency_code(currencyCode)
        if not is_valid_date_format(travel_date):
            raise ValueError("Travel date must be in YYYY-MM-DD format")
            
        if return_date and not is_valid_date_format(return_date):
            raise ValueError("Return date must be in YYYY-MM-DD format")
            
        if return_date and return_date < travel_date:
            raise ValueError("Return date cannot be before travel date")
            
        logger.info(
            f"Searching flights: {source} -> {destination} on {travel_date}"
            f"{' (round trip)' if return_date else ''}, "
            f"{adults} adults, {children} children, {infants} infants, "
            f"Class: {travel_class}, Currency: {currencyCode}, "
            f"Max price: {'None' if max_price is None else f'{max_price} {currencyCode}'}"
        )
        try:
            # Prepare the base parameters
            params = {
                'currencyCode' : currencyCode,
                'originLocationCode': source,
                'destinationLocationCode': destination,
                'departureDate': travel_date,
                'adults': adults,
                'max': max_results
            }
            
            # Only include children parameter if there are children
            if children > 0:
                params['children'] = children
                
            # Only include infants parameter if there are infants
            if infants > 0:
                params['infants'] = infants
                
            # Include boolean parameters only if they are True
            if include_business_class is False:
                params['includedAirlineCodes'] = '!O'  # Exclude business class
                
            if include_premium_economy is False:
                params['includedAirlineCodes'] = params.get('includedAirlineCodes', '') + '!P'
                
            if non_stop:
                params['nonStop'] = 'true'
                
            if max_price is not None:
                params['maxPrice'] = int(max_price)  # Convert to int as API expects integer values
                
            # Make the API call with retry logic
            response = call_with_retry(
                self.client.shopping.flight_offers_search.get,
                **params
            )
            
            logger.debug(f"Amadeus response: {response}")
            
            # Debug the response structure and save to file
            # debug_amadeus_response(response)
            
            # Process the response data
            flights = response.data
            logger.debug(f"Processed {len(flights) if flights else 0} flights")
           
            if not response.data:
                return []
                        
            flights = response.data
            #if(return_date):
                #save_response_to_file(response.data,"full_return_itineary")
                    
            # Sort the flights using the provided sort function
            try:
                flights.sort(key=sort_func)
            except Exception as e:
                logger.warning(f"Error sorting flights with provided sort function: {e}")
                # Fall back to default sorting by duration if custom sort fails
               # flights.sort(key=sort_by_duration)
                        
            return flights
            
        except ResponseError as error:
            logging.error(f"Amadeus API error: {error}")
            logger.error(
                "Searching flights with params: "
                f"date={travel_date}, origin={source}, "
                f"destination={destination}, adults={adults}, children={children}, "
                f"include_business={include_business_class}, "
                f"include_premium_economy={include_premium_economy}, non_stop={non_stop}, "
                f"max_price={max_price}"
            )
            raise Exception(f"Failed to search flights: {error}")
    
    def _validate_airport_code(self, code: str, param_name: str) -> None:
        """
        Validate that an airport code is valid (3 uppercase letters).
        
        Args:
            code: The airport code to validate
            param_name: The name of the parameter for error messages
            
        Raises:
            ValueError: If the airport code is invalid
        """
        if not isinstance(code, str) or not code.isalpha() or len(code) != 3 or not code.isupper():
            raise ValueError(f"{param_name} must be a 3-letter uppercase IATA code, got: {code}")



    def _validate_passenger_count(self, adults: int, children: int, infants: int) -> None:
        """
        Validate passenger counts.
        
        Args:
            adults: Number of adult passengers
            children: Number of child passengers
            infants: Number of infant passengers
            
        Raises:
            ValueError: If any passenger count is invalid
        """
        if not isinstance(adults, int) or adults < 1 or adults > 9:
            raise ValueError("Number of adults must be between 1 and 9")
        if not isinstance(children, int) or children < 0 or children > 8:
            raise ValueError("Number of children must be between 0 and 8")
        if not isinstance(infants, int) or infants < 0 or infants > 5:
            raise ValueError("Number of infants must be between 0 and 5")
        if adults + children + infants > 9:
            raise ValueError("Total number of passengers cannot exceed 9")
        if infants > adults:
            raise ValueError("Number of infants cannot exceed number of adults")

    def _validate_travel_class(self, travel_class: str) -> None:
        """
        Validate travel class.
        
        Args:
            travel_class: Travel class to validate (e.g., 'ECONOMY', 'BUSINESS')
            
        Raises:
            ValueError: If travel class is invalid or None
        """
        if not isinstance(travel_class, str) or not travel_class.strip():
            raise ValueError(f"Travel class must be a non-empty string")
            
        if travel_class.upper() not in VALID_TRAVEL_CLASSES:
            raise ValueError(f"Travel class must be one of {', '.join(VALID_TRAVEL_CLASSES)}")

def is_valid_date_format(date_str) -> bool:
    """Validate the date format is YYYY-MM-DD.
    
    Args:
        date_str: Date string to validate (can be any type)
        
    Returns:
        bool: True if format is valid and represents a valid date, False otherwise
    """
    # Check if input is string
    if not isinstance(date_str, str):
        return False
        
    # Check format YYYY-MM-DD with regex
    import re
    if not re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
        return False
        
    # Check if it's a valid date
    try:
        year, month, day = map(int, date_str.split('-'))
        # Check if the date is valid (handles months with different days, leap years, etc.)
        datetime(year=year, month=month, day=day)
        return True
    except (ValueError, TypeError):
        return False


def validate_return_date(end_date: str, start_date: str) -> None:
    """Validate return date is in correct format and after travel date.
    
    Args:
        end_date: Return date string in YYYY-MM-DD format or None
        start_date: Travel date string in YYYY-MM-DD format or None
        
    Raises:
        ValueError: If return date is invalid or before travel date
    """
    if end_date is None or start_date is None:
        return  # No return date or no start date to validate against
        
    if not is_valid_date_format(end_date):
        raise ValueError("Return date must be in YYYY-MM-DD format")
        
    if not is_valid_date_format(start_date):
        raise ValueError("Start date must be in YYYY-MM-DD format")

    # Ensure return date is after or equal to travel date
    travel_dt = datetime.strptime(start_date, '%Y-%m-%d').date()
    return_dt = datetime.strptime(end_date, '%Y-%m-%d').date()
    if return_dt < travel_dt:
        raise ValueError("End date must be on or after the start date")


def validate_currency_code(currency_code: str) -> None:
    """Validate currency code format (3-letter ISO code).
    
    Args:
        currency_code: Currency code to validate (e.g., 'USD', 'EUR', 'INR')
        
    Raises:
        ValueError: If currency code is invalid
    """
    #TODO: Ensure that it is validated and caps on the upstream. 
    if not isinstance(currency_code, str) or len(currency_code.strip()) != 3 or not currency_code.isalpha() or currency_code != currency_code.upper():
        raise ValueError(
            f"Invalid currency code: {currency_code}. "
            "Must be a 3-letter ISO code (e.g., 'USD', 'EUR', 'INR')"
        )


#TODO: To be removed, as of now, just declared because we need it in these debugging functions. 
mcpSearchFlight = None


 # --- 1. Define Your Tool as a Python Function ---
    # Tools are essentially Python functions that your LLM can "call" (or rather,
    # request to be called). It's crucial to provide a clear docstring, as this
    # is often how LLMs understand the tool's purpose and its parameters.

# --- 2. Represent the Tool Schema (JSON Schema) ---
# LLMs often understand tools via JSON Schema definitions. You can manually define
# this, or libraries might help extract it from function signatures and docstrings.

def get_tool_json_schema(func) -> Dict[str, Any]:
    """
    Generates a basic JSON Schema for a given function, primarily from its docstring.
    This is a simplified example.
    """
    if func.__name__ == "search_flights":
        return {
            "type": "function",
            "function": {
                "name": "search_flights",
                "description": "Searches for available flights between a source and destination on a given date.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "travel_date": {
                            "type": "string",
                            "description": "The desired date of travel in 'YYYY-MM-DD' format."
                        },
                        "source": {
                            "type": "string",
                            "description": "The departure airport code (e.g., 'SFO', 'LAX') or city name."
                        },
                        "destination": {
                            "type": "string",
                            "description": "The arrival airport code (e.g., 'JFK', 'LHR') or city name."
                        }
                    },
                    "required": ["travel_date", "source", "destination"]
                }
            }
        }
    else:
        raise ValueError(f"Schema generation not implemented for {func.__name__}")



# --- 3. Conceptual Integration with Llama Model ---
# When interacting with a Llama model (e.g., via Llama.cpp, Hugging Face transformers,
# or a specific Llama API), you typically pass tools as part of the system or user prompt.
# Llama 3.x specifically supports JSON-based tool calling.

def generate_llama_prompt_with_tools(user_query: str, tools_schema: List[Dict]) -> List[Dict]:
    """
    Constructs a chat history in a format suitable for Llama models
    that support tool calling (e.g., Llama 3.x).

    Args:
        user_query (str): The user's natural language query.
        tools_schema (List[Dict]): A list of JSON schemas for the available tools.

    Returns:
        List[Dict]: A list of message dictionaries representing the chat history.
    """
    # Llama 3.x prompt format (simplified for this example)
    # The 'system' role is often used to define tools.
    # The exact format might vary slightly based on the Llama version and client library.
    return [
        {"role": "system", "content": f"You are a helpful assistant with access to the following tools:\n{json.dumps(tools_schema, indent=2)}\n\nWhen a user asks a question that can be answered by a tool, generate a tool call in JSON format."},
        {"role": "user", "content": user_query}
    ]



# --- 4. Conceptual Interaction with an MCP Server ---
# The Model Context Protocol (MCP) defines a way for LLMs to dynamically
# discover and interact with tools and resources. An MCP server would expose
# your 'search_flights' function as a tool.

# An MCP client (e.g., using the `mcp-server-sqlite` or `mirascope` libraries
# as suggested by search results) would:
# 1. Connect to the MCP server.
# 2. Discover available tools (which would include `search_flights`).
# 3. Present these tool definitions (schemas) to the Llama model (as shown above).
# 4. When Llama generates a tool call (e.g., `{"name": "search_flights", "parameters": {"travel_date": "2025-07-20", "source": "SFO", "destination": "JFK"}}`),
#    the MCP client (or its executor) would:
#    a. Parse Llama's output to extract the tool name and arguments.
#    b. Call the actual Python function (`search_flights(**args)`).
#    c. Send the function's result back to the Llama model for a final, coherent response.

class MCPClientSimulator:
    """
    A very basic simulator to illustrate how an MCP client would
    interpret Llama's output and execute a tool.
    In a real scenario, this would be handled by a sophisticated client library
    that communicates with a running MCP server.
    """
    def __init__(self, available_tools_functions: Dict[str, callable]):
        self.available_tools = available_tools_functions

    def process_llama_output(self, llama_output_json: Dict) -> Optional[Dict]:
        """
        Simulates parsing Llama's tool call output and executing the tool.
        """
        if not isinstance(llama_output_json, dict) or "tool_calls" not in llama_output_json:
            print("Llama output does not contain a tool call or is not in expected format.")
            return None

        for tool_call in llama_output_json["tool_calls"]:
            tool_name = tool_call.get("name")
            tool_args = tool_call.get("parameters", {})

            if tool_name and tool_name in self.available_tools:
                print(f"\n--- MCP Client Simulator: Executing Tool '{tool_name}' ---")
                print(f"Arguments: {tool_args}")
                try:
                    result = self.available_tools[tool_name](**tool_args)
                    print(f"Tool Result: {result}")
                    return {"tool_output": result, "tool_name": tool_name}
                except TypeError as e:
                    print(f"Error executing tool '{tool_name}': Invalid arguments. {e}")
                    return {"error": f"Invalid arguments for {tool_name}", "details": str(e)}
                except Exception as e:
                    print(f"Error executing tool '{tool_name}': {e}")
                    return {"error": f"Tool execution failed for {tool_name}", "details": str(e)}
            else:
                print(f"MCP Client Simulator: Unknown or unavailable tool '{tool_name}'.")
        return None



# --- Sending Tool Output Back to Llama (Conceptual) ---
# After the MCP client executes the tool, its output needs to be sent back
# to the Llama model, often in a new message with a specific role (e.g., 'ipython'
# in Llama 3.1/3.3).

def continue_llama_conversation_with_tool_output(
    previous_chat_history: List[Dict],
    tool_name: str,
    tool_input: Dict,
    tool_output: Any # Changed to Any to accommodate list of flights
) -> List[Dict]:
    """
    Adds the tool call and its output to the chat history for Llama to continue.
    """
    # This structure is inspired by Llama 3.1/3.3's `ipython` role for tool output.
    # The model then uses this context to formulate a human-readable response.
    tool_call_message = {
        "role": "assistant",
        "content": f"call: {tool_name}({json.dumps(tool_input)})" # Llama might generate this format
    }
    tool_output_message = {
        "role": "tool", # Or 'ipython' for Llama 3.x
        "content": json.dumps(tool_output)
    }
    return previous_chat_history + [tool_call_message, tool_output_message]

def main():
    """
    Main function to test flight search functionality.
    Allows interactive testing of the search_flights function with predefined examples.
    """

    # Get the schema for our defined tool
    flight_search_tool_schema = get_tool_json_schema(mcpSearchFlight.search_flights)

    print("--- Generated Tool JSON Schema ---")
    print(json.dumps(flight_search_tool_schema, indent=2))
    print("\n")

    # Simulate Llama's output for a tool call (what Llama *would* generate)
    # This is NOT actual Llama generation, but what we expect it to produce.
    simulated_llama_output_1 = {
        "tool_calls": [
            {
                "name": "search_flights",
                "parameters": {
                    "travel_date": "2025-07-20",
                    "return_date": "2025-08-21",
                    "source": "HYD",
                    "destination": "JFK",
                    "adults": 1,
                    "children": 1,
                    "infants": 1,
                    "travel_class": "ECONOMY",
                    "max_results": 225,
                    "include_business_class": True,
                    "include_premium_economy": True,
                    "non_stop": False,
                    "max_price": 10000,
                    "currencyCode": "USD"

                }
            }
        ]
    }

    simulated_llama_output_2 = {
        "tool_calls": [
            {
                "name": "search_flights",
                "parameters": {
                    "travel_date": "2025-08-10",
                    "source": "LAX",
                    "destination": "LHR"
                }
            }
        ]
    }
    # Instantiate the simulator with our defined tool
    mcp_simulator = MCPClientSimulator({"search_flights": mcpSearchFlight.search_flights})

    # Process the simulated Llama output
    tool_result_1 = mcp_simulator.process_llama_output(simulated_llama_output_1)
    print(f"Result for Llama output 1: {tool_result_1}")

    tool_result_2 = mcp_simulator.process_llama_output(simulated_llama_output_2)
    print(f"Result for Llama output 2: {tool_result_2}")
    # Example user queries for flight search
    user_query_1 = "Find me flights from San Francisco to New York on July 20, 2025."
    user_query_2 = "Are there any flights from LAX to London Heathrow on August 10, 2025?"

    # Prepare the prompt for the Llama model
    llama_prompt_1 = generate_llama_prompt_with_tools(user_query_1, [flight_search_tool_schema])
    llama_prompt_2 = generate_llama_prompt_with_tools(user_query_2, [flight_search_tool_schema])

    print("--- Example Llama Prompt 1 (Conceptual) ---")
    print(json.dumps(llama_prompt_1, indent=2))
    print("\n")

    print("--- Example Llama Prompt 2 (Conceptual) ---")
    print(json.dumps(llama_prompt_2, indent=2))
    print("\n")
    
    if tool_result_1:
        refined_llama_prompt_1 = continue_llama_conversation_with_tool_output(
            llama_prompt_1,
            "search_flights",
            simulated_llama_output_1["tool_calls"][0]["parameters"],
            tool_result_1
        )
        print("\n--- Refined Llama Prompt 1 with Tool Output (Conceptual) ---")
        print(json.dumps(refined_llama_prompt_1, indent=2))
    # Predefined test cases
    examples = [
        {"date": "2025-07-20", "source": "SFO", "destination": "JFK", "description": "Example 1: San Francisco to New York"},
        {"date": "2025-08-10", "source": "LAX", "destination": "LHR", "description": "Example 2: Los Angeles to London"},
        {"date": "2025-09-01", "source": "NYC", "destination": "LAX", "description": "Example 3: New York to Los Angeles (no results)"}
    ]
    
    display_menu()
    process_menu_loop(examples)

def display_menu():
    """Display the main menu options."""
    print("\n=== Flight Search Debugger ===")
    print("Available options:")
    print("1. Run predefined examples")
    print("2. Enter custom search")
    print("q. Quit\n")

def run_predefined_examples(examples):
    """Run through all predefined flight search examples.
    
    Args:
        examples (list): List of example searches with date, source, and destination
    """
    print("\n" + "="*50)
    print("RUNNING PREDEFINED EXAMPLES")
    print("="*50)
    for example in examples:
        print(f"\n{example['description']}")
        print("-" * len(example['description']))
        mcpSearchFlight.search_flights(travel_date=example['date'], source=example['source'], destination=example['destination'])
        print("\n" + "-"*50)


def parse_search_input(user_input: str) -> tuple[str, str, str] | None:
    """Parse and validate user input for flight search.
    
    Args:
        user_input (str): Raw input from user
        
    Returns:
        tuple[str, str, str] | None: Tuple of (date_str, source, destination) if valid, 
                                    None if input is invalid
    """
    if user_input.lower() == 'back':
        return None
        
    try:
        date_str, source, destination = user_input.split()
        
        if not is_valid_date_format(date_str):
            print("Error: Date must be in YYYY-MM-DD format")
            return None
            
        return date_str, source, destination
        
    except ValueError:
        print("Error: Invalid input format")
        print("Please use format: YYYY-MM-DD SOURCE DESTINATION (e.g., 2025-07-20 SFO JFK)")
        return None

def custom_search_loop():
    """Handle custom flight search input from the user."""
    print("\nEnter flight search parameters (press Ctrl+C to return to menu)")
    print("Format: YYYY-MM-DD SOURCE DESTINATION (e.g., 2025-07-20 SFO JFK)")
    
    while True:
        try:
            user_input = input("\nEnter [date] [source] [destination] (or 'back' to return): ").strip()
            
            if user_input.lower() == 'back':
                break
                
            result = parse_search_input(user_input)
            if result:
                date_str, source, destination = result
                mcpSearchFlight.search_flights(date_str, source, destination)
                
        except KeyboardInterrupt:
            print("\nReturning to main menu...")
            break

def process_menu_loop(examples):
    """Process user input for the main menu.
    
    Args:
        examples (list): List of example searches with date, source, and destination
    """

    # --- Example Execution of the Tool ---
    print("\n--- Direct Example Execution of search_flights ---")
    # Example 1: A flight that should return results
    example_flights_1 =mcpSearchFlight.search_flights(travel_date="2025-07-20", source="SFO", destination="HYD")
    print(f"Direct Call Result (SFO to JFK, July 20, 2025): {json.dumps(example_flights_1, indent=2)}")

    print("\n")

    # Example 2: A flight that should return no results (based on mock data)
    example_flights_2 = mcpSearchFlight.search_flights(travel_date="2025-09-01", source="NYC", destination="LAX")
    print(f"Direct Call Result (NYC to LAX, Sept 01, 2025): {json.dumps(example_flights_2, indent=2)}")

    print("\n")

    # Example 3: Another flight that should return results
    example_flights_3 =mcpSearchFlight.search_flights(travel_date="2025-08-10", source="LAX", destination="LHR")
    print(f"Direct Call Result (LAX to LHR, Aug 10, 2025): {json.dumps(example_flights_3, indent=2)}")
    
    while True:
        try:
            choice = input("Select an option (1/2/q): ").strip().lower()
            
            if choice == 'q':
                print("Exiting...")
                break
                
            elif choice == '1':
                run_predefined_examples(examples)
                
            elif choice == '2':
                custom_search_loop()
                
            else:
                print("Invalid choice. Please select 1, 2, or q.")
                
            print("\n" + "="*50 + "\n")
            display_menu()
            
        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"An unexpected error occurred: {e}")

def save_response_to_file(response_data: dict, filename_prefix: str = "flight_search_response") -> Optional[str]:
    """
    Save API response data to a timestamped JSON file.
    
    Args:
        response_data: The data to save to file
        filename_prefix: Prefix for the output filename
        
    Returns:
        str: The filename if successful, None otherwise
    """
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{filename_prefix}_{timestamp}.json"
        with open(filename, 'w') as f:
            json.dump(response_data, f, indent=2)
        logger.debug(f"Saved API response to {filename}")
        return filename
    except Exception as e:
        logger.error(f"Failed to save API response to file: {e}")
        return None


def debug_amadeus_response(response):
    """
    Debug and log the structure of the Amadeus API response.
    Saves the response to a timestamped JSON file for further analysis.
    
    Args:
        response: The response object from Amadeus API
    """
    if not response:
        logger.warning("Empty response received from Amadeus API")
        return
        
    # Save response to file
    save_response_to_file(response.data, "flight_search_response")
        
    try:
        # Log basic response info
        logger.info("=== AMADEUS API RESPONSE DEBUG ===")
        logger.info(f"Response type: {type(response).__name__}")
        
        # Check if response has data attribute
        if not hasattr(response, 'data'):
            logger.warning("Response does not contain 'data' attribute")
            return
            
        data = response.data
        logger.info(f"Found {len(data) if data else 0} flight offers")
        
        if not data:
            logger.info("No flight offers found in the response")
            return
            
        # Debug first flight offer in detail
        first_offer = data[0]
        logger.info("\n=== FIRST FLIGHT OFFER ===")
        logger.info(f"Offer Id : {first_offer['id']}")
        logger.info(f"Offer Type : {first_offer['type']}")
        # Basic offer info
        if 'id' in first_offer:
            logger.info(f"Offer ID: {first_offer['id']}")
        if 'type' in first_offer:
            logger.info(f"Offer type: {first_offer['type']}")
            
        # Itinerary info
        if 'itineraries' in first_offer and first_offer['itineraries']:
            itinerary = first_offer['itineraries'][0]
            logger.info("\n=== ITINERARY ===")
            logger.info(f"Duration: {itinerary.get('duration', 'N/A')}")
            logger.info(f"Number of segments: {len(itinerary.get('segments', []))}")
            logger.info(f"Number of stops: {itinerary.get('numberOfStops', 'N/A')}")
      
            # Itineraries
            logger.info("\n=== ITINERARIES ===")
            for i, itin in enumerate(first_offer.get('itineraries', []), 1):
                logger.info(f"\nItinerary {i} (Duration: {itin.get('duration', 'N/A')})")
                
                for j, segment in enumerate(itin.get('segments', []), 1):
                    logger.info(f"  Segment {j}:")
                    if 'departure' in segment:
                        dep = segment['departure']
                        logger.info(f"    Departure: {dep.get('iataCode', 'N/A')} at {dep.get('at', 'N/A')}")
                    if 'arrival' in segment:
                        arr = segment['arrival']
                        logger.info(f"    Arrival: {arr.get('iataCode', 'N/A')} at {arr.get('at', 'N/A')}")
                    if 'carrierCode' in segment:
                        logger.info(f"    Airline: {segment.get('carrierCode', 'N/A')} {segment.get('number', '')}")
                            
        # Traveler pricings
        if 'travelerPricings' in first_offer and first_offer['travelerPricings']:
            logger.info("\n=== TRAVELER PRICING ===")
            for i, pricing in enumerate(first_offer['travelerPricings'], 1):
                logger.info(f"\nTraveler {i} (Type: {pricing.get('travelerType', 'N/A')}):")
                if 'price' in pricing:
                    price = pricing['price']
                    logger.info(f"  Price: {price.get('total', 'N/A')} {price.get('currency', '')}")
                    
        logger.info("\n=== END OF DEBUG INFO ===\n")
        
    except Exception as e:
        logger.error(f"Error in debug_amadeus_response: {str(e)}", exc_info=True)


if __name__ == "__main__":
    # Configure logging to show DEBUG level messages
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
        ]
    )
    mcpSearchFlight = FlightSearchMCP()
    main()
