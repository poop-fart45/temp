from typing import Dict, List, Optional
from langchain.chat_models import AzureChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
from django.conf import settings
from datetime import datetime
from quotes.models import GPTPromptConfig


class QuoteItem(BaseModel):
    """Model for individual items in a quote."""
    item_number: Optional[str] = Field(None, description="Item/part number")
    description: Optional[str] = Field(None, description="Description of the item")
    quantity: Optional[float] = Field(None, description="Quantity ordered")
    unit_price: Optional[float] = Field(None, description="Price per unit")
    unit_of_measure: Optional[str] = Field("EA", description="Unit of measure (e.g., EA, FT, LBS)")


class QuoteData(BaseModel):
    """Model for the complete quote data."""
    supplier_name: Optional[str] = Field(None, description="Name of the supplier")
    quote_number: Optional[str] = Field(None, description="Quote reference number")
    quote_date: Optional[str] = Field(None, description="Date of the quote in YYYY-MM-DD format")
    items: List[QuoteItem] = Field(default_factory=list, description="List of items in the quote")


class GPTExtractor:
    def __init__(self):
        self.llm = AzureChatOpenAI(
            openai_api_key=settings.AZURE_OPENAI_API_KEY,
            openai_api_base=settings.AZURE_OPENAI_ENDPOINT,
            deployment_name=settings.AZURE_OPENAI_DEPLOYMENT_NAME,
            openai_api_version="2024-02-15-preview",
            temperature=0,  # We want consistent results
        )
        self.parser = PydanticOutputParser(pydantic_object=QuoteData)

    def _get_active_prompt_config(self) -> tuple[str, str]:
        """Get the active prompt configuration from the database."""
        try:
            config = GPTPromptConfig.objects.get(is_active=True)
            return config.system_prompt, config.user_prompt
        except GPTPromptConfig.DoesNotExist:
            # Return default prompts if no active config exists
            return (
                """You are a precise quote data extractor. Your task is to extract structured data from supplier quotes.
                Important guidelines:
                1. Extract ONLY factual information present in the text
                2. For dates, ensure they are in YYYY-MM-DD format
                3. For numbers, ensure they are converted to proper numerical values
                4. For item numbers, preserve exact formatting
                5. If a value is clearly missing, use null
                6. For unit prices, extract the individual unit price, not total price
                7. If unit of measure is not specified, use 'EA' for each

                The output should match this format exactly:
                {format_instructions}
                """,
                "Please extract the quote information from the following text:\n\n{text_content}"
            )

    def _create_extraction_prompt(self) -> ChatPromptTemplate:
        """Create the prompt template for quote extraction."""
        system_prompt, user_prompt = self._get_active_prompt_config()
        return ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("user", user_prompt)
        ])

    def _preprocess_text(self, text: str) -> str:
        """Clean and prepare text for processing."""
        # Remove multiple spaces and normalize newlines
        text = ' '.join(text.split())
        # Remove any unusual characters that might interfere with processing
        text = ''.join(char for char in text if ord(char) < 128)
        return text

    def _validate_date(self, date_str: Optional[str]) -> Optional[str]:
        """Validate and format the date string."""
        if not date_str:
            return None
        try:
            # Try to parse the date
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            return date_obj.strftime('%Y-%m-%d')
        except ValueError:
            # If parsing fails, return today's date
            return datetime.now().strftime('%Y-%m-%d')

    def _validate_quote_data(self, quote_data: QuoteData) -> QuoteData:
        """Validate and clean the extracted quote data."""
        # Ensure quote date is in correct format if present
        if quote_data.quote_date:
            quote_data.quote_date = self._validate_date(quote_data.quote_date)
        
        # Clean up items
        for item in quote_data.items:
            # Ensure positive numbers if present
            if item.quantity is not None:
                item.quantity = abs(item.quantity)
            if item.unit_price is not None:
                item.unit_price = abs(item.unit_price)
            
            # Normalize unit of measure if present
            if item.unit_of_measure:
                item.unit_of_measure = item.unit_of_measure.upper().strip()
            else:
                item.unit_of_measure = 'EA'
        
        return quote_data

    def extract_quote_data(self, text_content: str) -> QuoteData:
        """Extract structured quote data from text content using GPT-4."""
        try:
            # Preprocess the text
            cleaned_text = self._preprocess_text(text_content)
            
            # Create and format the prompt
            prompt = self._create_extraction_prompt()
            formatted_prompt = prompt.format_messages(
                format_instructions=self.parser.get_format_instructions(),
                text_content=cleaned_text
            )

            # Get response from GPT
            response = self.llm.invoke(formatted_prompt)
            
            # Parse the response into QuoteData
            quote_data = self.parser.parse(response.content)
            
            # Validate and clean the data
            validated_data = self._validate_quote_data(quote_data)
            
            return validated_data

        except Exception as e:
            # Log the error (you might want to add proper logging here)
            print(f"Error extracting quote data: {str(e)}")
            # Return a minimal valid quote data object
            return QuoteData(
                supplier_name=None,
                quote_number=None,
                quote_date=datetime.now().strftime('%Y-%m-%d'),
                items=[]
            ) 