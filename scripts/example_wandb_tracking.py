"""
Example script showing how to use W&B tracking in the Legal Graph System
This demonstrates logging metrics, configs, and artifacts during processing
"""
import sys
from pathlib import Path
import asyncio
import random
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import settings
from app.services.openai_service import openai_service
from app.core.database import SessionLocal
from app.models.legal_act import LegalAct
import logging

# Try to import wandb
try:
    import wandb
    WANDB_AVAILABLE = True
except ImportError:
    WANDB_AVAILABLE = False
    print("wandb not installed. Install with: pip install wandb")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def example_extraction_tracking():
    """
    Example: Track extraction process with W&B
    """
    if not WANDB_AVAILABLE:
        logger.error("wandb not available")
        return
    
    # Initialize W&B run
    run = wandb.init(
        # Use your entity/team name from config or default
        entity=settings.WANDB_ENTITY,
        # Project name from config
        project=settings.WANDB_PROJECT or "legal-graph-system",
        # Track hyperparameters and metadata
        config={
            "model": settings.OPENAI_MODEL,
            "max_response_tokens": settings.OPENAI_MAX_RESPONSE_TOKENS,
            "max_chat_tokens": settings.OPENAI_MAX_CHAT_TOKENS,
            "chunking_enabled": True,
            "max_chunk_size": 40000,
        },
        # Tags for organization
        tags=["extraction", "legal-acts", "demo"],
        # Notes about this run
        notes="Example run for tracking legal act extraction"
    )
    
    try:
        db = SessionLocal()
        
        # Get some acts to process
        acts = db.query(LegalAct).filter(
            LegalAct.is_processed == False,
            LegalAct.text.isnot(None)
        ).limit(5).all()
        
        logger.info(f"Processing {len(acts)} acts with W&B tracking...")
        
        # Simulate processing multiple acts
        total_elements = 0
        total_categories = 0
        processing_times = []
        
        for idx, act in enumerate(acts):
            start_time = datetime.now()
            
            try:
                # Extract elements (this will be tracked by W&B autolog if enabled)
                result = await openai_service.extract_set_elements(
                    legal_act_text=act.text[:50000],  # Limit text for demo
                    act_title=act.title,
                    categories=[]
                )
                
                # Calculate metrics
                elements_count = len(result.get("elements", []))
                categories_count = len(result.get("categories", []))
                processing_time = (datetime.now() - start_time).total_seconds()
                
                total_elements += elements_count
                total_categories += categories_count
                processing_times.append(processing_time)
                
                # Log metrics for this act
                run.log({
                    f"act_{idx}_elements": elements_count,
                    f"act_{idx}_categories": categories_count,
                    f"act_{idx}_processing_time": processing_time,
                    "total_elements": total_elements,
                    "total_categories": total_categories,
                    "acts_processed": idx + 1,
                })
                
                logger.info(f"Processed {act.nreg}: {elements_count} elements, {categories_count} categories")
                
            except Exception as e:
                logger.error(f"Error processing {act.nreg}: {e}")
                run.log({"errors": wandb.run.summary.get("errors", 0) + 1})
        
        # Log summary metrics
        if processing_times:
            avg_time = sum(processing_times) / len(processing_times)
            run.summary.update({
                "avg_processing_time": avg_time,
                "total_acts_processed": len(acts),
                "avg_elements_per_act": total_elements / len(acts) if acts else 0,
                "avg_categories_per_act": total_categories / len(acts) if acts else 0,
            })
        
        db.close()
        
    except Exception as e:
        logger.error(f"Error in example: {e}")
        run.log({"error": str(e)})
    finally:
        # Finish the run
        run.finish()
        logger.info("W&B run finished. Check your dashboard!")


def example_simple_tracking():
    """
    Simple example: Track simulated metrics (similar to W&B quickstart)
    """
    if not WANDB_AVAILABLE:
        logger.error("wandb not available")
        return
    
    # Initialize W&B run
    run = wandb.init(
        entity=settings.WANDB_ENTITY,
        project=settings.WANDB_PROJECT or "legal-graph-system",
        config={
            "learning_rate": 0.02,
            "architecture": "GPT-4o",
            "dataset": "Ukrainian Legal Acts",
            "epochs": 10,
        },
        tags=["simulation", "demo"],
    )
    
    # Simulate training/processing metrics
    epochs = 10
    offset = random.random() / 5
    
    for epoch in range(2, epochs):
        # Simulate metrics
        accuracy = 1 - 2**-epoch - random.random() / epoch - offset
        loss = 2**-epoch + random.random() / epoch + offset
        extraction_rate = accuracy * 100  # Simulated extraction success rate
        
        # Log metrics to wandb
        run.log({
            "accuracy": accuracy,
            "loss": loss,
            "extraction_rate": extraction_rate,
            "epoch": epoch,
        })
        
        logger.info(f"Epoch {epoch}: accuracy={accuracy:.3f}, loss={loss:.3f}")
    
    # Log final summary
    run.summary.update({
        "final_accuracy": accuracy,
        "final_loss": loss,
        "best_epoch": epochs - 1,
    })
    
    # Finish the run
    run.finish()
    logger.info("Simple tracking example finished!")


async def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="W&B tracking examples")
    parser.add_argument(
        "--example",
        type=str,
        choices=["simple", "extraction"],
        default="simple",
        help="Which example to run"
    )
    
    args = parser.parse_args()
    
    # Check W&B configuration
    if not settings.WANDB_ENABLED:
        logger.warning("W&B is disabled in config. Set WANDB_ENABLED=true to enable.")
        return
    
    if not settings.WANDB_API_KEY:
        logger.warning("WANDB_API_KEY not set. You may need to run 'wandb login' first.")
        logger.info("Or set WANDB_API_KEY in .env file")
    
    if args.example == "simple":
        example_simple_tracking()
    elif args.example == "extraction":
        await example_extraction_tracking()


if __name__ == "__main__":
    asyncio.run(main())



