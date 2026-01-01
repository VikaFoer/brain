"""
Service for OpenAI fine-tuning with Weights & Biases integration
"""
from openai import OpenAI
from typing import Dict, List, Any, Optional
from app.core.config import settings
import logging
import json
import os

logger = logging.getLogger(__name__)

# Try to import wandb, but don't fail if not installed
try:
    import wandb
    from wandb.integration.openai import autolog as wandb_autolog
    WANDB_AVAILABLE = True
except ImportError:
    WANDB_AVAILABLE = False
    logger.warning("wandb not installed. W&B integration will be disabled.")


class FineTuningService:
    """Service for fine-tuning OpenAI models with W&B tracking"""
    
    def __init__(self):
        if not settings.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY not configured")
        
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.wandb_enabled = settings.WANDB_ENABLED and WANDB_AVAILABLE
        
        # Initialize W&B if enabled
        if self.wandb_enabled:
            try:
                if settings.WANDB_API_KEY:
                    os.environ["WANDB_API_KEY"] = settings.WANDB_API_KEY
                
                # Initialize W&B
                wandb.init(
                    project=settings.WANDB_PROJECT,
                    entity=settings.WANDB_ENTITY,
                    config={
                        "openai_model": settings.OPENAI_MODEL,
                        "max_response_tokens": settings.OPENAI_MAX_RESPONSE_TOKENS,
                    }
                )
                
                # Enable OpenAI autologging for W&B
                wandb_autolog()
                logger.info(f"W&B initialized for project: {settings.WANDB_PROJECT}")
                
            except Exception as e:
                logger.warning(f"Failed to initialize W&B: {e}. Continuing without W&B.")
                self.wandb_enabled = False
        else:
            logger.info("W&B is disabled or not available")
    
    def prepare_training_data(
        self,
        training_examples: List[Dict[str, Any]]
    ) -> str:
        """
        Prepare training data in JSONL format for fine-tuning
        
        Args:
            training_examples: List of training examples, each containing:
                {
                    "messages": [
                        {"role": "system", "content": "..."},
                        {"role": "user", "content": "..."},
                        {"role": "assistant", "content": "..."}
                    ]
                }
        
        Returns:
            Path to JSONL file
        """
        import tempfile
        
        # Create temporary file
        temp_file = tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.jsonl',
            delete=False,
            encoding='utf-8'
        )
        
        try:
            # Write each example as a JSON line
            for example in training_examples:
                json_line = json.dumps(example, ensure_ascii=False)
                temp_file.write(json_line + '\n')
            
            temp_file_path = temp_file.name
            logger.info(f"Created training file with {len(training_examples)} examples: {temp_file_path}")
            
            return temp_file_path
            
        finally:
            temp_file.close()
    
    def upload_training_file(
        self,
        file_path: str
    ) -> str:
        """
        Upload training file to OpenAI
        
        Args:
            file_path: Path to JSONL training file
        
        Returns:
            File ID from OpenAI
        """
        try:
            with open(file_path, 'rb') as f:
                file_response = self.client.files.create(
                    file=f,
                    purpose='fine-tune'
                )
            
            file_id = file_response.id
            logger.info(f"Uploaded training file. File ID: {file_id}")
            
            if self.wandb_enabled:
                wandb.log({"training_file_id": file_id})
            
            return file_id
            
        except Exception as e:
            logger.error(f"Error uploading training file: {e}")
            raise
    
    def create_fine_tune_job(
        self,
        training_file_id: str,
        validation_file_id: Optional[str] = None,
        base_model: str = "gpt-4o-mini",  # GPT-4o-mini is recommended for fine-tuning
        hyperparameters: Optional[Dict[str, Any]] = None,
        suffix: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a fine-tuning job
        
        Args:
            training_file_id: ID of uploaded training file
            validation_file_id: Optional ID of validation file
            base_model: Base model to fine-tune (gpt-4o-mini, gpt-3.5-turbo, etc.)
            hyperparameters: Optional hyperparameters (n_epochs, batch_size, learning_rate_multiplier)
            suffix: Optional suffix for fine-tuned model name
        
        Returns:
            Fine-tuning job information
        """
        try:
            job_params = {
                "training_file": training_file_id,
                "model": base_model,
            }
            
            if validation_file_id:
                job_params["validation_file"] = validation_file_id
            
            if suffix:
                job_params["suffix"] = suffix
            
            if hyperparameters:
                job_params["hyperparameters"] = hyperparameters
            
            # Create fine-tuning job
            fine_tune_job = self.client.fine_tuning.jobs.create(**job_params)
            
            job_id = fine_tune_job.id
            logger.info(f"Created fine-tuning job. Job ID: {job_id}")
            
            if self.wandb_enabled:
                wandb.log({
                    "fine_tune_job_id": job_id,
                    "base_model": base_model,
                    "training_file_id": training_file_id,
                })
                if hyperparameters:
                    wandb.config.update(hyperparameters)
            
            return {
                "job_id": job_id,
                "status": fine_tune_job.status,
                "model": fine_tune_job.model,
                "fine_tuned_model": fine_tune_job.fine_tuned_model,
                "created_at": fine_tune_job.created_at,
            }
            
        except Exception as e:
            logger.error(f"Error creating fine-tuning job: {e}")
            raise
    
    def get_fine_tune_status(self, job_id: str) -> Dict[str, Any]:
        """
        Get status of a fine-tuning job
        
        Args:
            job_id: Fine-tuning job ID
        
        Returns:
            Job status information
        """
        try:
            job = self.client.fine_tuning.jobs.retrieve(job_id)
            
            status_info = {
                "job_id": job.id,
                "status": job.status,
                "model": job.model,
                "fine_tuned_model": job.fine_tuned_model,
                "trained_tokens": job.trained_tokens,
                "error": job.error.model_dump() if job.error else None,
            }
            
            if self.wandb_enabled:
                wandb.log({
                    "job_status": job.status,
                    "trained_tokens": job.trained_tokens or 0,
                })
            
            return status_info
            
        except Exception as e:
            logger.error(f"Error getting fine-tuning job status: {e}")
            raise
    
    def list_fine_tune_events(self, job_id: str) -> List[Dict[str, Any]]:
        """
        List events for a fine-tuning job
        
        Args:
            job_id: Fine-tuning job ID
        
        Returns:
            List of events
        """
        try:
            events = self.client.fine_tuning.jobs.list_events(job_id=job_id, limit=50)
            
            event_list = []
            for event in events.data:
                event_list.append({
                    "id": event.id,
                    "created_at": event.created_at,
                    "level": event.level,
                    "message": event.message,
                })
            
            if self.wandb_enabled:
                wandb.log({"events_count": len(event_list)})
            
            return event_list
            
        except Exception as e:
            logger.error(f"Error listing fine-tuning events: {e}")
            raise
    
    def cancel_fine_tune_job(self, job_id: str) -> Dict[str, Any]:
        """
        Cancel a fine-tuning job
        
        Args:
            job_id: Fine-tuning job ID
        
        Returns:
            Cancellation result
        """
        try:
            job = self.client.fine_tuning.jobs.cancel(job_id)
            
            logger.info(f"Cancelled fine-tuning job: {job_id}")
            
            if self.wandb_enabled:
                wandb.log({"job_cancelled": True, "job_id": job_id})
            
            return {
                "job_id": job.id,
                "status": job.status,
            }
            
        except Exception as e:
            logger.error(f"Error cancelling fine-tuning job: {e}")
            raise
    
    def cleanup(self):
        """Cleanup resources (close W&B if needed)"""
        if self.wandb_enabled:
            try:
                wandb.finish()
            except Exception as e:
                logger.warning(f"Error finishing W&B: {e}")



