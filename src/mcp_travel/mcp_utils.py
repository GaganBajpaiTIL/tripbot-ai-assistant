from datetime import datetime
import logging
import parsedatetime as pdt
from fastmcp import FastMCP, tools

# Import logging configuration
from tripbot.config.logging_config import setup_logging

# Initialize logging
setup_logging()
logger = logging.getLogger(__name__)

# Supported date formats for parsing
DATE_FORMATS = [
    "%Y-%m-%d",  # 2025-12-31
    "%m/%d/%Y",  # 12/31/2025
    "%d/%m/%Y",  # 31/12/2025
    "%Y%m%d",    # 20251231
]

def parseDate(date_str: str, date_format: str = "%Y-%m-%d") -> str:
    """
    Parse a natural language date string into a formatted date string.
    
    Args:
        date_str: Natural language date string (e.g., "next Sunday")
        date_format: Output date format (default: "%Y-%m-%d")
        
    Returns:
        Formatted date string in the specified format
        
    Example:
        >>> parseDate("next Sunday")
        '2025-08-24'
    """
    try:
        logger.debug(f"Parsing date string: {date_str}")
        
        # First, try parsing as natural language
        cal = pdt.Calendar()
        time_struct, parse_status = cal.parse(date_str)
        if parse_status:
            result = datetime(*time_struct[:6]).strftime(date_format)
            logger.debug(f"Successfully parsed as natural language date. Result: {result}")
            return result
        
        # If natural language parsing fails, check standard date formats
        for fmt in DATE_FORMATS:
            try:
                # If we can parse it with this format, it's already a date string
                dt = datetime.strptime(date_str, fmt)
                result = dt.strftime(date_format)
                logger.debug(f"Successfully parsed with format {fmt}. Result: {result}")
                return result
            except ValueError:
                continue
        
        # If we get here, no format matched, return today's date
        logger.warning(f"Could not parse date string: {date_str}. Returning today's date.")
        return datetime.now().strftime(date_format)
    except Exception as e:
        # In case of any error, return today's date as fallback
        logger.error(f"Error parsing date string '{date_str}': {str(e)}")
        return datetime.now().strftime(date_format)

# Example usage with FastMCP
if __name__ == "__main__":
    import asyncio
    import argparse
    import json
    
    async def main():
        # Initialize FastMCP
        mcp = FastMCP()
        
        # Register the tool
        mcp.tool(parseDate)
        from fastmcp import Client
        async with Client(mcp) as client:
            # Discover what tools are available on the server
            tools = await client.list_tools()
            logger.info("Discovered tools:")
            for i, tool in enumerate(tools, 1):
                logger.info(f"  Tool {i}: Name={getattr(tool, 'name', 'N/A')}, "
                          f"Description={getattr(tool, 'description', 'N/A')}, "
                          f"Parameters={getattr(tool, 'parameters', 'N/A')}")
                logger.debug(f"Full tool info: {tool}")    
    # Run the async main function
    asyncio.run(main())
     # Rest of your code remains the same
    parser = argparse.ArgumentParser(description='Parse natural language dates')
    parser.add_argument('--date', type=str, help='Natural language date string (e.g., "next Sunday")')
    parser.add_argument('--format', type=str, default="%Y-%m-%d", 
                          help='Output date format (default: %Y-%m-%d)')
        
    args = parser.parse_args()
        
    if args.date:
        result = parseDate(args.date, args.format)
        print(json.dumps({"result": result}))
    else:
        print("Enter dates to parse (or 'quit' to exit):")
        try:
            while True:
                try:
                    user_input = input("\nDate to parse> ").strip()
                    if user_input.lower() in ('quit', 'exit', 'q'):
                        print("Exiting...")
                        break
                    if not user_input:
                        continue
                    result = parseDate(user_input, args.format)
                    print(f"Result: {result}")
                except KeyboardInterrupt:
                    break
                except Exception as e:
                    print(f"Error: {e}")
        except KeyboardInterrupt:
            print("\nExiting...")