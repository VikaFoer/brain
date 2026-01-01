"""
Example: Using W&B Weave for LLM tracing
Based on W&B Weave quickstart guide
"""
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import settings
import logging

# Try to import weave
try:
    import weave
    from openai import OpenAI
    WEAVE_AVAILABLE = True
except ImportError:
    WEAVE_AVAILABLE = False
    print("weave not installed. Install with: pip install weave openai")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def setup_environment():
    """Setup environment variables"""
    # Set W&B API key
    if settings.WANDB_API_KEY:
        os.environ['WANDB_API_KEY'] = settings.WANDB_API_KEY
    else:
        logger.warning("WANDB_API_KEY not set. Set it in .env file")
    
    # Set OpenAI API key (should already be set, but check)
    if settings.OPENAI_API_KEY:
        os.environ['OPENAI_API_KEY'] = settings.OPENAI_API_KEY
    else:
        logger.warning("OPENAI_API_KEY not set. Set it in .env file")


def example_basic_tracing():
    """
    Basic example: Trace OpenAI API calls with Weave
    Based on W&B Weave quickstart
    """
    if not WEAVE_AVAILABLE:
        logger.error("weave not available. Install with: pip install weave")
        return
    
    setup_environment()
    
    # Initialize weave
    project_name = f"{settings.WANDB_ENTITY or 'user'}/{settings.WANDB_PROJECT or 'legal-graph-system'}"
    weave.init(f"{project_name}/weave-tracing-example")
    
    logger.info(f"Weave initialized for project: {project_name}")
    
    # Define function with weave.op decorator to track requests
    @weave.op  # Decorator to track requests
    def create_completion(message: str) -> str:
        """Create OpenAI chat completion"""
        client = OpenAI()
        response = client.chat.completions.create(
            model=settings.OPENAI_MODEL or "gpt-4o",
            messages=[
                {"role": "system", "content": "Ти експерт з аналізу нормативно-правових актів України."},
                {"role": "user", "content": message}
            ],
        )
        return response.choices[0].message.content
    
    # Call the function - this will be traced in Weave
    message = "Що таке нормативно-правовий акт?"
    logger.info(f"Sending message: {message}")
    
    result = create_completion(message)
    logger.info(f"Received response: {result[:100]}...")
    
    logger.info("Check your W&B dashboard to see the trace!")


def example_extraction_tracing():
    """
    Example: Trace legal act extraction with Weave
    """
    if not WEAVE_AVAILABLE:
        logger.error("weave not available. Install with: pip install weave")
        return
    
    setup_environment()
    
    # Initialize weave
    project_name = f"{settings.WANDB_ENTITY or 'user'}/{settings.WANDB_PROJECT or 'legal-graph-system'}"
    weave.init(f"{project_name}/extraction-tracing")
    
    from textwrap import dedent
    
    # Define extraction function with tracing
    @weave.op
    def extract_legal_elements(act_title: str, act_text: str) -> dict:
        """
        Extract elements from legal act text
        This will be traced in Weave
        """
        client = OpenAI()
        
        system_prompt = """Ти експерт з аналізу нормативно-правових актів України. 
Твоя задача - виділити з тексту акту елементи множини та їх зв'язки."""
        
        user_prompt = f"""Проаналізуй наступний нормативно-правовий акт:

Назва: {act_title}

Текст:
{act_text[:5000]}

Виділи основні категорії та елементи множини."""
        
        response = client.chat.completions.create(
            model=settings.OPENAI_MODEL or "gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
        )
        
        import json
        result = json.loads(response.choices[0].message.content)
        return result
    
    # Example usage
    example_title = "Закон України про інформацію"
    example_text = """
    Стаття 1. Цей Закон регулює відносини, що виникають у сфері інформації...
    Стаття 2. Основні поняття, що використовуються в цьому Законі...
    """
    
    logger.info(f"Extracting elements from: {example_title}")
    result = extract_legal_elements(example_title, example_text)
    
    logger.info(f"Extracted {len(result.get('categories', []))} categories")
    logger.info("Check your W&B dashboard to see the trace with inputs and outputs!")


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="W&B Weave tracing examples")
    parser.add_argument(
        "--example",
        type=str,
        choices=["basic", "extraction"],
        default="basic",
        help="Which example to run"
    )
    
    args = parser.parse_args()
    
    if args.example == "basic":
        example_basic_tracing()
    elif args.example == "extraction":
        example_extraction_tracing()


if __name__ == "__main__":
    main()



