"""
Script to run fine-tuning with W&B integration
"""
import sys
import os
import argparse
from pathlib import Path
import time

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.fine_tuning_service import FineTuningService
from app.core.config import settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Run OpenAI fine-tuning with W&B")
    parser.add_argument(
        "--training-file",
        type=str,
        required=True,
        help="Path to training JSONL file (or OpenAI file ID)"
    )
    parser.add_argument(
        "--validation-file",
        type=str,
        default=None,
        help="Path to validation JSONL file (or OpenAI file ID, optional)"
    )
    parser.add_argument(
        "--base-model",
        type=str,
        default="gpt-4o-mini",
        help="Base model to fine-tune (default: gpt-4o-mini)"
    )
    parser.add_argument(
        "--suffix",
        type=str,
        default=None,
        help="Suffix for fine-tuned model name"
    )
    parser.add_argument(
        "--n-epochs",
        type=int,
        default=None,
        help="Number of epochs (default: auto)"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=None,
        help="Batch size (default: auto)"
    )
    parser.add_argument(
        "--learning-rate",
        type=float,
        default=None,
        help="Learning rate multiplier (default: auto)"
    )
    parser.add_argument(
        "--monitor",
        action="store_true",
        help="Monitor job status until completion"
    )
    parser.add_argument(
        "--upload",
        action="store_true",
        help="Upload local files to OpenAI (if paths provided)"
    )
    
    args = parser.parse_args()
    
    # Initialize fine-tuning service
    service = FineTuningService()
    
    try:
        # Handle file uploads if needed
        training_file_id = args.training_file
        validation_file_id = args.validation_file
        
        if args.upload and os.path.exists(args.training_file):
            logger.info(f"Uploading training file: {args.training_file}")
            training_file_id = service.upload_training_file(args.training_file)
            logger.info(f"Training file uploaded. File ID: {training_file_id}")
        
        if args.validation_file and args.upload and os.path.exists(args.validation_file):
            logger.info(f"Uploading validation file: {args.validation_file}")
            validation_file_id = service.upload_training_file(args.validation_file)
            logger.info(f"Validation file uploaded. File ID: {validation_file_id}")
        
        # Prepare hyperparameters
        hyperparameters = {}
        if args.n_epochs:
            hyperparameters["n_epochs"] = args.n_epochs
        if args.batch_size:
            hyperparameters["batch_size"] = args.batch_size
        if args.learning_rate:
            hyperparameters["learning_rate_multiplier"] = args.learning_rate
        
        # Create fine-tuning job
        logger.info("Creating fine-tuning job...")
        job_info = service.create_fine_tune_job(
            training_file_id=training_file_id,
            validation_file_id=validation_file_id,
            base_model=args.base_model,
            hyperparameters=hyperparameters if hyperparameters else None,
            suffix=args.suffix
        )
        
        job_id = job_info["job_id"]
        logger.info(f"Fine-tuning job created!")
        logger.info(f"Job ID: {job_id}")
        logger.info(f"Status: {job_info['status']}")
        logger.info(f"Base model: {args.base_model}")
        
        if service.wandb_enabled:
            logger.info(f"W&B project: {settings.WANDB_PROJECT}")
            logger.info(f"View logs at: https://wandb.ai/{settings.WANDB_ENTITY or 'your-entity'}/{settings.WANDB_PROJECT}")
        
        # Monitor job if requested
        if args.monitor:
            logger.info("Monitoring job status...")
            while True:
                status_info = service.get_fine_tune_status(job_id)
                status = status_info["status"]
                
                logger.info(f"Job status: {status}")
                
                if status == "succeeded":
                    logger.info(f"Fine-tuning completed successfully!")
                    logger.info(f"Fine-tuned model: {status_info['fine_tuned_model']}")
                    if status_info.get("trained_tokens"):
                        logger.info(f"Trained tokens: {status_info['trained_tokens']}")
                    break
                elif status == "failed":
                    error = status_info.get("error")
                    logger.error(f"Fine-tuning failed: {error}")
                    break
                elif status in ["cancelled", "cancelling"]:
                    logger.info("Fine-tuning was cancelled")
                    break
                
                # Wait before next check
                time.sleep(30)
        
        else:
            logger.info(f"Job ID: {job_id}")
            logger.info("Use --monitor flag to watch job progress")
            logger.info(f"Or check status with: service.get_fine_tune_status('{job_id}')")
        
    except KeyboardInterrupt:
        logger.info("\nInterrupted by user")
        if job_id:
            response = input("Cancel fine-tuning job? (y/n): ")
            if response.lower() == 'y':
                service.cancel_fine_tune_job(job_id)
                logger.info("Job cancelled")
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
    finally:
        service.cleanup()


if __name__ == "__main__":
    main()



