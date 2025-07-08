import os
import google.generativeai as genai
from datetime import datetime
import pytz
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure Gemini
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found in environment variables")
genai.configure(api_key=GEMINI_API_KEY)

# Configure safety settings
safety_settings = [
    {
        "category": "HARM_CATEGORY_HARASSMENT",
        "threshold": "BLOCK_NONE",
    },
    {
        "category": "HARM_CATEGORY_HATE_SPEECH",
        "threshold": "BLOCK_NONE",
    },
    {
        "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
        "threshold": "BLOCK_NONE",
    },
    {
        "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
        "threshold": "BLOCK_NONE",
    },
]

# Initialize the model with safety settings
model = genai.GenerativeModel('models/gemini-1.5-pro-latest', safety_settings=safety_settings)

def parse_datetime_with_gemini(datetime_str: str) -> str:
    """
    Parse a datetime string using Gemini and return an ISO format string in US/Pacific timezone.
    
    Args:
        datetime_str (str): The datetime string to parse (can be in various formats)
        
    Returns:
        str: ISO format datetime string in US/Pacific timezone
        
    Raises:
        ValueError: If Gemini fails to parse the datetime or returns invalid format
    """
    try:
        prompt = f"""
        You are a datetime parser. Convert the input to ISO format (YYYY-MM-DDTHH:MM:SS) in US/Pacific timezone.

        Rules:
        - Return ONLY the ISO datetime string, no code, no explanations
        - Format: YYYY-MM-DDTHH:MM:SS
        - Timezone: US/Pacific (America/Los_Angeles)
        - If no time specified, use 00:00:00
        - If no date specified, use today's date
        - For relative dates like "next Monday", calculate the actual date
        - For "tomorrow", add 1 day to today
        - For "next week Monday", find the next Monday

        Input: {datetime_str}
        
        Response (ISO format only): """
        
        response = model.generate_content(prompt)
        parsed_datetime = response.text.strip()
        
        # Clean up the response - remove any markdown or code blocks
        if '```' in parsed_datetime:
            # Extract content between code blocks
            parts = parsed_datetime.split('```')
            if len(parts) >= 2:
                parsed_datetime = parts[1].strip()
                # Remove language identifier if present
                if '\n' in parsed_datetime:
                    parsed_datetime = parsed_datetime.split('\n', 1)[1]
        
        # Remove any remaining code or explanations
        parsed_datetime = parsed_datetime.split('\n')[0].strip()
        
        # Validate the response is a valid ISO format datetime
        try:
            # Parse the datetime to validate it
            dt = datetime.fromisoformat(parsed_datetime)
            
            # Always convert to US/Pacific using pytz for correct tzinfo
            pacific = pytz.timezone('America/Los_Angeles')
            # Remove tzinfo if present, then localize
            dt_naive = dt.replace(tzinfo=None)
            dt_pacific = pacific.localize(dt_naive)
            
            # Return in ISO format with Pacific timezone
            return dt_pacific.isoformat()
            
        except ValueError as e:
            logger.error(f"Invalid datetime format returned by Gemini: {parsed_datetime}")
            raise ValueError(f"Gemini returned invalid datetime format: {parsed_datetime}")
            
    except Exception as e:
        logger.error(f"Error parsing datetime with Gemini: {str(e)}")
        raise ValueError(f"Failed to parse datetime: {str(e)}")

def parse_datetime_range_with_gemini(datetime_str: str) -> tuple[str, str]:
    """
    Parse a datetime range string using Gemini and return start and end ISO format strings in US/Pacific timezone.
    
    Args:
        datetime_str (str): The datetime range string to parse (can be in various formats)
        
    Returns:
        tuple[str, str]: Tuple of (start_datetime, end_datetime) in ISO format
        
    Raises:
        ValueError: If Gemini fails to parse the datetime range or returns invalid format
    """
    try:
        prompt = f"""
        You are a datetime range parser. Convert the input to two ISO format strings (YYYY-MM-DDTHH:MM:SS) in US/Pacific timezone.

        Rules:
        - Return ONLY two ISO datetime strings separated by a comma
        - Format: YYYY-MM-DDTHH:MM:SS,YYYY-MM-DDTHH:MM:SS
        - Timezone: US/Pacific (America/Los_Angeles)
        - If no time specified, use 00:00:00 for start and 23:59:59 for end
        - If no date specified, use today's date
        - For relative dates, calculate the actual dates
        - NO CODE, NO EXPLANATIONS, NO MARKDOWN

        Input: {datetime_str}
        
        Response (two ISO formats separated by comma only): """
        
        response = model.generate_content(prompt)
        parsed_range = response.text.strip()
        
        # Clean up the response - remove any markdown or code blocks
        if '```' in parsed_range:
            # Extract content between code blocks
            parts = parsed_range.split('```')
            if len(parts) >= 2:
                parsed_range = parts[1].strip()
                # Remove language identifier if present
                if '\n' in parsed_range:
                    parsed_range = parsed_range.split('\n', 1)[1]
        
        # Remove any remaining code or explanations
        parsed_range = parsed_range.split('\n')[0].strip()
        
        # Remove any Python code patterns
        if parsed_range.startswith('import ') or parsed_range.startswith('from '):
            raise ValueError(f"Gemini returned Python code instead of datetime range: {parsed_range}")
        
        try:
            # Split the range into start and end
            start_str, end_str = parsed_range.split(',')
            start_str = start_str.strip()
            end_str = end_str.strip()
            
            # Parse and validate both datetimes
            pacific = pytz.timezone('America/Los_Angeles')
            
            # Parse start datetime
            start_dt = datetime.fromisoformat(start_str)
            # Always convert to US/Pacific using pytz for correct tzinfo
            start_dt_naive = start_dt.replace(tzinfo=None)
            start_dt_pacific = pacific.localize(start_dt_naive)
            
            # Parse end datetime
            end_dt = datetime.fromisoformat(end_str)
            end_dt_naive = end_dt.replace(tzinfo=None)
            end_dt_pacific = pacific.localize(end_dt_naive)
            
            # Return both in ISO format
            return start_dt_pacific.isoformat(), end_dt_pacific.isoformat()
            
        except ValueError as e:
            logger.error(f"Invalid datetime range format returned by Gemini: {parsed_range}")
            raise ValueError(f"Gemini returned invalid datetime range format: {parsed_range}")
            
    except Exception as e:
        logger.error(f"Error parsing datetime range with Gemini: {str(e)}")
        raise ValueError(f"Failed to parse datetime range: {str(e)}") 