"""
Model training and deployment pipeline for the autonomous AI ecosystem.

This module implements dataset preparation, model training orchestration,
evaluation, and deployment systems for language models and other AI models.
"""

import asyncio
import json
import os
import random
import shutil
import subprocess
import tempfile
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
import uuid
import hashlib

from ..core.interfaces import AgentModule
from ..core.logger import get_agent_logger, log_agent_event
from .dataset_manager import DatasetManager, KnowledgeEntry, KnowledgeCategory


class ModelType(Enum):
    """Types of models that can be trained."""
    LANGUAGE_MODEL = "language_model"
    CLASSIFICATION = "classification"
    EMBEDDING = "embedding"
    QUESTION_ANSWERING = "question_answering"
    SUMMARIZATION = "summarization"
    CODE_GENERATION = "code_generation"
    REASONING = "reasoning"
    MULTIMODAL = "multimodal"


class TrainingStatus(Enum):
    """Status of training jobs."""
    QUEUED = "queued"
    PREPARING = "preparing"
    TRAINING = "training"
    EVALUATING = "evaluating"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    DEPLOYED = "deployed"


@dataclass
class TrainingConfig:
    """Configuration for model training."""
    model_type: ModelType
    base_model: str = "gpt2-small"  # Base model to fine-tune from
    
    # Training parameters
    learning_rate: float = 5e-5
    batch_size: int = 8
    num_epochs: int = 3
    max_sequence_length: int = 512
    warmup_steps: int = 100
    
    # Data parameters
    train_split: float = 0.8
    validation_split: float = 0.1
    test_split: float = 0.1
    min_quality_threshold: float = 0.6
    
    # Resource constraints
    max_training_time_hours: float = 24.0
    max_memory_gb: float = 16.0
    use_gpu: bool = True
    
    # Output configuration
    save_checkpoints: bool = True
    checkpoint_frequency: int = 1000
    evaluate_frequency: int = 500
    
    # Advanced options
    gradient_accumulation_steps: int = 1
    weight_decay: float = 0.01
    adam_epsilon: float = 1e-8
    max_grad_norm: float = 1.0
    
    # Custom parameters
    custom_params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ModelEvaluation:
    """Results of model evaluation."""
    evaluation_id: str
    model_id: str
    evaluator_id: str
    
    # Metrics
    accuracy: float = 0.0
    precision: float = 0.0
    recall: float = 0.0
    f1_score: float = 0.0
    perplexity: float = float('inf')
    bleu_score: float = 0.0
    
    # Custom metrics
    custom_metrics: Dict[str, float] = field(default_factory=dict)
    
    # Evaluation details
    test_samples: int = 0
    evaluation_time: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    
    # Qualitative assessment
    human_rating: Optional[float] = None
    feedback: str = ""
    
    def get_overall_score(self) -> float:
        """Calculate overall model performance score."""
        scores = []
        
        if self.accuracy > 0:
            scores.append(self.accuracy)
        if self.f1_score > 0:
            scores.append(self.f1_score)
        if self.bleu_score > 0:
            scores.append(self.bleu_score)
        if self.perplexity < float('inf'):
            scores.append(1.0 / (1.0 + self.perplexity))  # Convert perplexity to 0-1 score
        
        # Add custom metrics
        for metric_value in self.custom_metrics.values():
            if 0 <= metric_value <= 1:
                scores.append(metric_value)
        
        return sum(scores) / len(scores) if scores else 0.0


@dataclass
class TrainingJob:
    """Represents a model training job."""
    job_id: str
    initiator_id: str
    model_name: str
    description: str
    
    # Configuration
    config: TrainingConfig
    dataset_ids: List[str]
    
    # Status and progress
    status: TrainingStatus = TrainingStatus.QUEUED
    progress_percentage: float = 0.0
    current_step: int = 0
    total_steps: int = 0
    
    # Timing
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    estimated_completion: Optional[datetime] = None
    
    # Results
    model_path: Optional[str] = None
    evaluation_results: List[ModelEvaluation] = field(default_factory=list)
    training_logs: List[str] = field(default_factory=list)
    
    # Resource usage
    memory_usage_gb: float = 0.0
    gpu_usage_percent: float = 0.0
    training_loss: List[float] = field(default_factory=list)
    validation_loss: List[float] = field(default_factory=list)
    
    # Error handling
    error_message: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def get_duration(self) -> float:
        """Get training duration in hours."""
        if not self.started_at:
            return 0.0
        
        end_time = self.completed_at or datetime.now()
        return (end_time - self.started_at).total_seconds() / 3600.0
    
    def add_log(self, message: str) -> None:
        """Add a log message to the training job."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.training_logs.append(f"[{timestamp}] {message}")
        
        # Limit log size
        if len(self.training_logs) > 1000:
            self.training_logs = self.training_logs[-1000:]


class ModelTrainer(AgentModule):
    """
    Model training and deployment pipeline for autonomous AI agents.
    
    Provides dataset preparation, model training orchestration, evaluation,
    and deployment capabilities for various types of AI models.
    """
    
    def __init__(self, agent_id: str, dataset_manager: DatasetManager, workspace_path: str = "model_workspace"):
        super().__init__(agent_id)
        self.dataset_manager = dataset_manager
        self.workspace_path = workspace_path
        self.logger = get_agent_logger(agent_id, "model_trainer")
        
        # Core data structures
        self.training_jobs: Dict[str, TrainingJob] = {}
        self.trained_models: Dict[str, Dict[str, Any]] = {}  # model_id -> model_info
        self.evaluation_results: Dict[str, List[ModelEvaluation]] = {}  # model_id -> evaluations
        
        # Training queue and workers
        self.training_queue = asyncio.Queue()
        self.active_jobs: Set[str] = set()
        self.max_concurrent_jobs = 2
        
        # System configuration
        self.config = {
            "max_dataset_size_gb": 10.0,
            "min_training_samples": 100,
            "max_training_samples": 1000000,
            "default_model_timeout_hours": 48.0,
            "checkpoint_retention_days": 30,
            "model_registry_path": os.path.join(workspace_path, "models"),
            "training_data_path": os.path.join(workspace_path, "training_data"),
            "evaluation_samples": 1000,
            "auto_deploy_threshold": 0.8
        }
        
        # Supported model frameworks
        self.frameworks = {
            "transformers": {
                "available": True,
                "models": ["gpt2", "bert", "roberta", "t5", "bart"],
                "tasks": [ModelType.LANGUAGE_MODEL, ModelType.CLASSIFICATION, ModelType.QUESTION_ANSWERING]
            },
            "pytorch": {
                "available": True,
                "models": ["custom"],
                "tasks": list(ModelType)
            }
        }
        
        # Statistics
        self.stats = {
            "total_jobs": 0,
            "completed_jobs": 0,
            "failed_jobs": 0,
            "total_training_hours": 0.0,
            "models_deployed": 0,
            "average_accuracy": 0.0,
            "datasets_processed": 0
        }
        
        # Counters
        self.job_counter = 0
        self.model_counter = 0
        self.evaluation_counter = 0
        
        self.logger.info("Model trainer initialized")
    
    async def initialize(self) -> None:
        """Initialize the model trainer."""
        try:
            # Create workspace directories
            os.makedirs(self.workspace_path, exist_ok=True)
            os.makedirs(self.config["model_registry_path"], exist_ok=True)
            os.makedirs(self.config["training_data_path"], exist_ok=True)
            
            # Start training workers
            for i in range(self.max_concurrent_jobs):
                asyncio.create_task(self._training_worker(f"worker_{i}"))
            
            # Start monitoring tasks
            asyncio.create_task(self._job_monitor())
            asyncio.create_task(self._cleanup_processor())
            
            # Check framework availability
            await self._check_framework_availability()
            
            self.logger.info("Model trainer initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize model trainer: {e}")
            raise
    
    async def shutdown(self) -> None:
        """Shutdown the model trainer."""
        try:
            # Cancel active jobs
            for job_id in list(self.active_jobs):
                await self.cancel_training_job(job_id)
            
            # Save training state
            await self._save_training_state()
            
            self.logger.info("Model trainer shutdown completed")
        except Exception as e:
            self.logger.error(f"Error during model trainer shutdown: {e}")
    
    async def submit_training_job(
        self,
        initiator_id: str,
        model_name: str,
        description: str,
        model_type: ModelType,
        dataset_ids: List[str],
        config: Optional[TrainingConfig] = None
    ) -> Dict[str, Any]:
        """Submit a new model training job."""
        try:
            # Validate datasets
            for dataset_id in dataset_ids:
                if dataset_id not in self.dataset_manager.datasets:
                    return {"success": False, "error": f"Dataset {dataset_id} not found"}
            
            # Use default config if not provided
            if config is None:
                config = TrainingConfig(model_type=model_type)
            
            # Validate configuration
            validation_result = await self._validate_training_config(config, dataset_ids)
            if not validation_result["valid"]:
                return {"success": False, "error": validation_result["error"]}
            
            # Create training job
            self.job_counter += 1
            job_id = f"job_{self.job_counter}_{datetime.now().timestamp()}"
            
            job = TrainingJob(
                job_id=job_id,
                initiator_id=initiator_id,
                model_name=model_name,
                description=description,
                config=config,
                dataset_ids=dataset_ids
            )
            
            # Estimate training time and steps
            total_samples = await self._estimate_dataset_size(dataset_ids)
            job.total_steps = (total_samples // config.batch_size) * config.num_epochs
            job.estimated_completion = datetime.now() + timedelta(
                hours=min(config.max_training_time_hours, job.total_steps * 0.001)  # Rough estimate
            )
            
            self.training_jobs[job_id] = job
            
            # Queue for training
            await self.training_queue.put(job_id)
            
            # Update statistics
            self.stats["total_jobs"] += 1
            
            log_agent_event(
                self.agent_id,
                "training_job_submitted",
                {
                    "job_id": job_id,
                    "initiator_id": initiator_id,
                    "model_name": model_name,
                    "model_type": model_type.value,
                    "dataset_count": len(dataset_ids)
                }
            )
            
            result = {
                "success": True,
                "job_id": job_id,
                "status": job.status.value,
                "estimated_completion": job.estimated_completion.isoformat() if job.estimated_completion else None,
                "total_steps": job.total_steps
            }
            
            self.logger.info(f"Training job submitted: {model_name} by {initiator_id}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to submit training job: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_training_job_status(self, job_id: str) -> Dict[str, Any]:
        """Get the status of a training job."""
        try:
            if job_id not in self.training_jobs:
                return {"error": "Training job not found"}
            
            job = self.training_jobs[job_id]
            
            # Calculate progress metrics
            progress_info = {
                "percentage": job.progress_percentage,
                "current_step": job.current_step,
                "total_steps": job.total_steps,
                "eta_hours": 0.0
            }
            
            if job.started_at and job.current_step > 0:
                elapsed_hours = (datetime.now() - job.started_at).total_seconds() / 3600.0
                steps_per_hour = job.current_step / elapsed_hours
                remaining_steps = job.total_steps - job.current_step
                progress_info["eta_hours"] = remaining_steps / max(1, steps_per_hour)
            
            # Get latest evaluation if available
            latest_evaluation = None
            if job.evaluation_results:
                latest_eval = max(job.evaluation_results, key=lambda e: e.timestamp)
                latest_evaluation = {
                    "overall_score": latest_eval.get_overall_score(),
                    "accuracy": latest_eval.accuracy,
                    "timestamp": latest_eval.timestamp.isoformat()
                }
            
            return {
                "job_id": job.job_id,
                "model_name": job.model_name,
                "status": job.status.value,
                "progress": progress_info,
                "created_at": job.created_at.isoformat(),
                "started_at": job.started_at.isoformat() if job.started_at else None,
                "completed_at": job.completed_at.isoformat() if job.completed_at else None,
                "duration_hours": job.get_duration(),
                "memory_usage_gb": job.memory_usage_gb,
                "gpu_usage_percent": job.gpu_usage_percent,
                "training_loss": job.training_loss[-10:] if job.training_loss else [],  # Last 10 values
                "validation_loss": job.validation_loss[-10:] if job.validation_loss else [],
                "latest_evaluation": latest_evaluation,
                "error_message": job.error_message,
                "recent_logs": job.training_logs[-20:] if job.training_logs else []  # Last 20 logs
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get training job status: {e}")
            return {"error": str(e)}
    
    async def cancel_training_job(self, job_id: str) -> Dict[str, Any]:
        """Cancel a training job."""
        try:
            if job_id not in self.training_jobs:
                return {"success": False, "error": "Training job not found"}
            
            job = self.training_jobs[job_id]
            
            if job.status in [TrainingStatus.COMPLETED, TrainingStatus.FAILED, TrainingStatus.CANCELLED]:
                return {"success": False, "error": f"Job already {job.status.value}"}
            
            # Cancel the job
            job.status = TrainingStatus.CANCELLED
            job.completed_at = datetime.now()
            job.add_log("Training job cancelled by user")
            
            # Remove from active jobs
            self.active_jobs.discard(job_id)
            
            log_agent_event(
                self.agent_id,
                "training_job_cancelled",
                {
                    "job_id": job_id,
                    "model_name": job.model_name,
                    "duration_hours": job.get_duration()
                }
            )
            
            result = {
                "success": True,
                "status": job.status.value,
                "duration_hours": job.get_duration()
            }
            
            self.logger.info(f"Training job cancelled: {job_id}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to cancel training job: {e}")
            return {"success": False, "error": str(e)}
    
    async def evaluate_model(
        self,
        evaluator_id: str,
        model_id: str,
        test_dataset_ids: Optional[List[str]] = None,
        custom_metrics: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Evaluate a trained model."""
        try:
            if model_id not in self.trained_models:
                return {"success": False, "error": "Model not found"}
            
            model_info = self.trained_models[model_id]
            
            # Prepare evaluation data
            if test_dataset_ids:
                test_data = await self._prepare_evaluation_data(test_dataset_ids)
            else:
                # Use default test data from training
                test_data = await self._get_default_test_data(model_id)
            
            if not test_data:
                return {"success": False, "error": "No test data available"}
            
            # Run evaluation
            self.evaluation_counter += 1
            evaluation_id = f"eval_{self.evaluation_counter}_{datetime.now().timestamp()}"
            
            evaluation = ModelEvaluation(
                evaluation_id=evaluation_id,
                model_id=model_id,
                evaluator_id=evaluator_id,
                test_samples=len(test_data)
            )
            
            # Perform evaluation (simplified)
            start_time = datetime.now()
            eval_results = await self._run_model_evaluation(model_info, test_data, custom_metrics)
            evaluation.evaluation_time = (datetime.now() - start_time).total_seconds()
            
            # Update evaluation with results
            evaluation.accuracy = eval_results.get("accuracy", 0.0)
            evaluation.precision = eval_results.get("precision", 0.0)
            evaluation.recall = eval_results.get("recall", 0.0)
            evaluation.f1_score = eval_results.get("f1_score", 0.0)
            evaluation.perplexity = eval_results.get("perplexity", float('inf'))
            evaluation.bleu_score = eval_results.get("bleu_score", 0.0)
            evaluation.custom_metrics = eval_results.get("custom_metrics", {})
            
            # Store evaluation
            if model_id not in self.evaluation_results:
                self.evaluation_results[model_id] = []
            self.evaluation_results[model_id].append(evaluation)
            
            # Update model info with latest evaluation
            model_info["latest_evaluation"] = evaluation.get_overall_score()
            model_info["last_evaluated"] = datetime.now().isoformat()
            
            log_agent_event(
                self.agent_id,
                "model_evaluated",
                {
                    "evaluation_id": evaluation_id,
                    "model_id": model_id,
                    "evaluator_id": evaluator_id,
                    "overall_score": evaluation.get_overall_score(),
                    "test_samples": evaluation.test_samples
                }
            )
            
            result = {
                "success": True,
                "evaluation_id": evaluation_id,
                "overall_score": evaluation.get_overall_score(),
                "metrics": {
                    "accuracy": evaluation.accuracy,
                    "precision": evaluation.precision,
                    "recall": evaluation.recall,
                    "f1_score": evaluation.f1_score,
                    "perplexity": evaluation.perplexity,
                    "bleu_score": evaluation.bleu_score
                },
                "custom_metrics": evaluation.custom_metrics,
                "test_samples": evaluation.test_samples,
                "evaluation_time": evaluation.evaluation_time
            }
            
            self.logger.info(f"Model evaluated: {model_id} (score: {evaluation.get_overall_score():.3f})")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to evaluate model: {e}")
            return {"success": False, "error": str(e)}"    

    async def deploy_model(
        self,
        deployer_id: str,
        model_id: str,
        deployment_name: str,
        deployment_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Deploy a trained model for use."""
        try:
            if model_id not in self.trained_models:
                return {"success": False, "error": "Model not found"}
            
            model_info = self.trained_models[model_id]
            
            # Check if model meets deployment criteria
            if "latest_evaluation" in model_info:
                if model_info["latest_evaluation"] < self.config["auto_deploy_threshold"]:
                    return {"success": False, "error": "Model quality below deployment threshold"}
            
            # Create deployment
            deployment_id = f"deploy_{model_id}_{datetime.now().timestamp()}"
            deployment_path = os.path.join(self.config["model_registry_path"], "deployed", deployment_name)
            
            # Copy model files to deployment location
            os.makedirs(deployment_path, exist_ok=True)
            if model_info.get("model_path") and os.path.exists(model_info["model_path"]):
                shutil.copytree(model_info["model_path"], deployment_path, dirs_exist_ok=True)
            
            # Create deployment metadata
            deployment_metadata = {
                "deployment_id": deployment_id,
                "model_id": model_id,
                "deployment_name": deployment_name,
                "deployer_id": deployer_id,
                "deployed_at": datetime.now().isoformat(),
                "model_info": model_info,
                "deployment_config": deployment_config or {},
                "status": "active"
            }
            
            # Save deployment metadata
            metadata_path = os.path.join(deployment_path, "deployment_metadata.json")
            with open(metadata_path, 'w') as f:
                json.dump(deployment_metadata, f, indent=2)
            
            # Update model info
            model_info["deployed"] = True
            model_info["deployment_id"] = deployment_id
            model_info["deployment_name"] = deployment_name
            model_info["deployed_at"] = datetime.now().isoformat()
            
            # Update statistics
            self.stats["models_deployed"] += 1
            
            log_agent_event(
                self.agent_id,
                "model_deployed",
                {
                    "deployment_id": deployment_id,
                    "model_id": model_id,
                    "deployment_name": deployment_name,
                    "deployer_id": deployer_id
                }
            )
            
            result = {
                "success": True,
                "deployment_id": deployment_id,
                "deployment_name": deployment_name,
                "deployment_path": deployment_path,
                "status": "active"
            }
            
            self.logger.info(f"Model deployed: {deployment_name} (model: {model_id})")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to deploy model: {e}")
            return {"success": False, "error": str(e)}
    
    def get_training_jobs(self, initiator_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get training jobs, optionally filtered by initiator."""
        try:
            jobs = []
            
            for job in self.training_jobs.values():
                if initiator_id and job.initiator_id != initiator_id:
                    continue
                
                job_info = {
                    "job_id": job.job_id,
                    "model_name": job.model_name,
                    "description": job.description,
                    "initiator_id": job.initiator_id,
                    "status": job.status.value,
                    "progress_percentage": job.progress_percentage,
                    "created_at": job.created_at.isoformat(),
                    "started_at": job.started_at.isoformat() if job.started_at else None,
                    "completed_at": job.completed_at.isoformat() if job.completed_at else None,
                    "duration_hours": job.get_duration(),
                    "model_type": job.config.model_type.value,
                    "dataset_count": len(job.dataset_ids)
                }
                
                jobs.append(job_info)
            
            # Sort by creation time (most recent first)
            jobs.sort(key=lambda j: j["created_at"], reverse=True)
            
            return jobs
            
        except Exception as e:
            self.logger.error(f"Failed to get training jobs: {e}")
            return []
    
    def get_trained_models(self) -> List[Dict[str, Any]]:
        """Get list of trained models."""
        try:
            models = []
            
            for model_id, model_info in self.trained_models.items():
                model_summary = {
                    "model_id": model_id,
                    "name": model_info.get("name", "Unknown"),
                    "type": model_info.get("type", "Unknown"),
                    "created_at": model_info.get("created_at", ""),
                    "training_job_id": model_info.get("training_job_id", ""),
                    "latest_evaluation": model_info.get("latest_evaluation", 0.0),
                    "deployed": model_info.get("deployed", False),
                    "deployment_name": model_info.get("deployment_name", ""),
                    "size_mb": model_info.get("size_mb", 0.0),
                    "parameters": model_info.get("parameters", 0)
                }
                
                models.append(model_summary)
            
            # Sort by creation time (most recent first)
            models.sort(key=lambda m: m["created_at"], reverse=True)
            
            return models
            
        except Exception as e:
            self.logger.error(f"Failed to get trained models: {e}")
            return []
    
    def get_model_evaluations(self, model_id: str) -> List[Dict[str, Any]]:
        """Get evaluations for a specific model."""
        try:
            if model_id not in self.evaluation_results:
                return []
            
            evaluations = []
            
            for eval_result in self.evaluation_results[model_id]:
                eval_info = {
                    "evaluation_id": eval_result.evaluation_id,
                    "evaluator_id": eval_result.evaluator_id,
                    "timestamp": eval_result.timestamp.isoformat(),
                    "overall_score": eval_result.get_overall_score(),
                    "metrics": {
                        "accuracy": eval_result.accuracy,
                        "precision": eval_result.precision,
                        "recall": eval_result.recall,
                        "f1_score": eval_result.f1_score,
                        "perplexity": eval_result.perplexity,
                        "bleu_score": eval_result.bleu_score
                    },
                    "custom_metrics": eval_result.custom_metrics,
                    "test_samples": eval_result.test_samples,
                    "evaluation_time": eval_result.evaluation_time,
                    "human_rating": eval_result.human_rating,
                    "feedback": eval_result.feedback
                }
                
                evaluations.append(eval_info)
            
            # Sort by timestamp (most recent first)
            evaluations.sort(key=lambda e: e["timestamp"], reverse=True)
            
            return evaluations
            
        except Exception as e:
            self.logger.error(f"Failed to get model evaluations: {e}")
            return []
    
    def get_training_stats(self) -> Dict[str, Any]:
        """Get training system statistics."""
        try:
            # Calculate success rate
            success_rate = (self.stats["completed_jobs"] / max(1, self.stats["total_jobs"])) * 100.0
            
            # Calculate average model quality
            all_evaluations = []
            for evaluations in self.evaluation_results.values():
                all_evaluations.extend(evaluations)
            
            avg_model_quality = 0.0
            if all_evaluations:
                avg_model_quality = sum(e.get_overall_score() for e in all_evaluations) / len(all_evaluations)
            
            # Job status breakdown
            status_breakdown = {}
            for status in TrainingStatus:
                status_breakdown[status.value] = len([
                    j for j in self.training_jobs.values() 
                    if j.status == status
                ])
            
            # Model type breakdown
            type_breakdown = {}
            for model_type in ModelType:
                type_breakdown[model_type.value] = len([
                    j for j in self.training_jobs.values() 
                    if j.config.model_type == model_type
                ])
            
            return {
                "total_jobs": self.stats["total_jobs"],
                "completed_jobs": self.stats["completed_jobs"],
                "failed_jobs": self.stats["failed_jobs"],
                "success_rate_percent": success_rate,
                "total_training_hours": self.stats["total_training_hours"],
                "models_deployed": self.stats["models_deployed"],
                "average_model_quality": avg_model_quality,
                "datasets_processed": self.stats["datasets_processed"],
                "active_jobs": len(self.active_jobs),
                "queued_jobs": self.training_queue.qsize(),
                "job_status_breakdown": status_breakdown,
                "model_type_breakdown": type_breakdown,
                "total_evaluations": len(all_evaluations),
                "framework_availability": self.frameworks
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get training stats: {e}")
            return {"error": str(e)}
    
    # Private helper methods
    
    async def _validate_training_config(self, config: TrainingConfig, dataset_ids: List[str]) -> Dict[str, Any]:
        """Validate training configuration."""
        try:
            # Check if model type is supported
            supported = False
            for framework_info in self.frameworks.values():
                if framework_info["available"] and config.model_type in framework_info["tasks"]:
                    supported = True
                    break
            
            if not supported:
                return {"valid": False, "error": f"Model type {config.model_type.value} not supported"}
            
            # Check dataset size
            total_samples = await self._estimate_dataset_size(dataset_ids)
            if total_samples < self.config["min_training_samples"]:
                return {"valid": False, "error": f"Insufficient training samples: {total_samples} < {self.config['min_training_samples']}"}
            
            if total_samples > self.config["max_training_samples"]:
                return {"valid": False, "error": f"Too many training samples: {total_samples} > {self.config['max_training_samples']}"}
            
            # Check resource constraints
            if config.max_memory_gb > 64.0:  # Reasonable limit
                return {"valid": False, "error": "Memory requirement too high"}
            
            if config.max_training_time_hours > 168.0:  # 1 week limit
                return {"valid": False, "error": "Training time limit too high"}
            
            return {"valid": True}
            
        except Exception as e:
            return {"valid": False, "error": str(e)}
    
    async def _estimate_dataset_size(self, dataset_ids: List[str]) -> int:
        """Estimate total number of training samples."""
        try:
            total_samples = 0
            
            for dataset_id in dataset_ids:
                if dataset_id in self.dataset_manager.datasets:
                    dataset = self.dataset_manager.datasets[dataset_id]
                    total_samples += dataset.total_entries
            
            return total_samples
            
        except Exception as e:
            self.logger.error(f"Error estimating dataset size: {e}")
            return 0
    
    async def _check_framework_availability(self) -> None:
        """Check availability of ML frameworks."""
        try:
            # Check transformers
            try:
                import transformers
                self.frameworks["transformers"]["available"] = True
                self.logger.info("Transformers framework available")
            except ImportError:
                self.frameworks["transformers"]["available"] = False
                self.logger.warning("Transformers framework not available")
            
            # Check PyTorch
            try:
                import torch
                self.frameworks["pytorch"]["available"] = True
                self.logger.info("PyTorch framework available")
            except ImportError:
                self.frameworks["pytorch"]["available"] = False
                self.logger.warning("PyTorch framework not available")
            
        except Exception as e:
            self.logger.error(f"Error checking framework availability: {e}")
    
    async def _training_worker(self, worker_id: str) -> None:
        """Background worker to process training jobs."""
        while True:
            try:
                # Get job from queue
                job_id = await asyncio.wait_for(self.training_queue.get(), timeout=1.0)
                
                if job_id not in self.training_jobs:
                    continue
                
                job = self.training_jobs[job_id]
                self.active_jobs.add(job_id)
                
                try:
                    # Process the training job
                    await self._process_training_job(job, worker_id)
                except Exception as e:
                    job.status = TrainingStatus.FAILED
                    job.error_message = str(e)
                    job.completed_at = datetime.now()
                    job.add_log(f"Training failed: {e}")
                    self.stats["failed_jobs"] += 1
                    
                    self.logger.error(f"Training job {job_id} failed: {e}")
                
                finally:
                    self.active_jobs.discard(job_id)
                    self.training_queue.task_done()
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                self.logger.error(f"Error in training worker {worker_id}: {e}")
                await asyncio.sleep(1)
    
    async def _process_training_job(self, job: TrainingJob, worker_id: str) -> None:
        """Process a single training job."""
        try:
            job.status = TrainingStatus.PREPARING
            job.started_at = datetime.now()
            job.add_log(f"Training started by worker {worker_id}")
            
            # Prepare training data
            job.add_log("Preparing training data...")
            training_data = await self._prepare_training_data(job)
            
            if not training_data:
                raise Exception("Failed to prepare training data")
            
            job.progress_percentage = 10.0
            job.add_log(f"Prepared {len(training_data)} training samples")
            
            # Start training
            job.status = TrainingStatus.TRAINING
            job.add_log("Starting model training...")
            
            # Simulate training process (in practice, this would call actual ML frameworks)
            model_path = await self._run_training(job, training_data)
            
            if not model_path:
                raise Exception("Training process failed")
            
            job.model_path = model_path
            job.progress_percentage = 80.0
            job.add_log(f"Training completed, model saved to {model_path}")
            
            # Evaluate model
            job.status = TrainingStatus.EVALUATING
            job.add_log("Evaluating trained model...")
            
            evaluation = await self._evaluate_trained_model(job)
            if evaluation:
                job.evaluation_results.append(evaluation)
                job.add_log(f"Evaluation completed, score: {evaluation.get_overall_score():.3f}")
            
            # Register model
            model_id = await self._register_trained_model(job)
            
            # Complete job
            job.status = TrainingStatus.COMPLETED
            job.completed_at = datetime.now()
            job.progress_percentage = 100.0
            job.add_log("Training job completed successfully")
            
            # Update statistics
            self.stats["completed_jobs"] += 1
            self.stats["total_training_hours"] += job.get_duration()
            
            log_agent_event(
                self.agent_id,
                "training_job_completed",
                {
                    "job_id": job.job_id,
                    "model_name": job.model_name,
                    "duration_hours": job.get_duration(),
                    "model_id": model_id
                }
            )
            
        except Exception as e:
            self.logger.error(f"Error processing training job: {e}")
            raise
    
    async def _prepare_training_data(self, job: TrainingJob) -> List[Dict[str, Any]]:
        """Prepare training data from datasets."""
        try:
            training_data = []
            
            for dataset_id in job.dataset_ids:
                if dataset_id not in self.dataset_manager.datasets:
                    continue
                
                # Get knowledge entries from dataset
                entries = await self._get_dataset_entries(dataset_id)
                
                # Filter by quality
                quality_threshold = job.config.min_quality_threshold
                filtered_entries = [
                    entry for entry in entries 
                    if entry.quality_score >= quality_threshold
                ]
                
                # Convert to training format
                for entry in filtered_entries:
                    training_sample = await self._convert_entry_to_training_sample(entry, job.config.model_type)
                    if training_sample:
                        training_data.append(training_sample)
            
            # Shuffle and limit data
            random.shuffle(training_data)
            if len(training_data) > self.config["max_training_samples"]:
                training_data = training_data[:self.config["max_training_samples"]]
            
            return training_data
            
        except Exception as e:
            self.logger.error(f"Error preparing training data: {e}")
            return []
    
    async def _get_dataset_entries(self, dataset_id: str) -> List[KnowledgeEntry]:
        """Get knowledge entries from a dataset."""
        try:
            # In a full implementation, this would properly track dataset membership
            # For now, return all entries (simplified)
            return list(self.dataset_manager.knowledge_entries.values())
            
        except Exception as e:
            self.logger.error(f"Error getting dataset entries: {e}")
            return []
    
    async def _convert_entry_to_training_sample(self, entry: KnowledgeEntry, model_type: ModelType) -> Optional[Dict[str, Any]]:
        """Convert a knowledge entry to a training sample."""
        try:
            if model_type == ModelType.LANGUAGE_MODEL:
                return {
                    "text": f"{entry.title}\n\n{entry.content}",
                    "labels": entry.content,
                    "metadata": {
                        "category": entry.category.value,
                        "quality": entry.quality_score
                    }
                }
            
            elif model_type == ModelType.CLASSIFICATION:
                return {
                    "text": entry.content,
                    "label": entry.category.value,
                    "metadata": {
                        "quality": entry.quality_score
                    }
                }
            
            elif model_type == ModelType.QUESTION_ANSWERING:
                # Generate question-answer pairs from content
                return {
                    "question": f"What is {entry.title}?",
                    "answer": entry.content,
                    "context": entry.content,
                    "metadata": {
                        "category": entry.category.value,
                        "quality": entry.quality_score
                    }
                }
            
            else:
                # Default format
                return {
                    "input": entry.title,
                    "output": entry.content,
                    "metadata": {
                        "category": entry.category.value,
                        "quality": entry.quality_score
                    }
                }
            
        except Exception as e:
            self.logger.error(f"Error converting entry to training sample: {e}")
            return None
    
    async def _run_training(self, job: TrainingJob, training_data: List[Dict[str, Any]]) -> Optional[str]:
        """Run the actual training process."""
        try:
            # Create model directory
            model_dir = os.path.join(self.config["model_registry_path"], "training", job.job_id)
            os.makedirs(model_dir, exist_ok=True)
            
            # Simulate training process
            # In a real implementation, this would use actual ML frameworks
            total_steps = len(training_data) // job.config.batch_size * job.config.num_epochs
            
            for step in range(total_steps):
                # Simulate training step
                await asyncio.sleep(0.01)  # Simulate computation time
                
                # Update progress
                job.current_step = step + 1
                job.progress_percentage = 10.0 + (step / total_steps) * 70.0
                
                # Simulate loss values
                if step % 10 == 0:
                    train_loss = 2.0 * (1.0 - step / total_steps) + random.uniform(-0.1, 0.1)
                    val_loss = train_loss + random.uniform(0.0, 0.2)
                    job.training_loss.append(max(0.1, train_loss))
                    job.validation_loss.append(max(0.1, val_loss))
                
                # Simulate resource usage
                job.memory_usage_gb = random.uniform(2.0, job.config.max_memory_gb * 0.8)
                job.gpu_usage_percent = random.uniform(70.0, 95.0) if job.config.use_gpu else 0.0
                
                # Add periodic logs
                if step % 100 == 0:
                    job.add_log(f"Step {step}/{total_steps}, loss: {job.training_loss[-1]:.4f}")
            
            # Save model (simplified)
            model_path = os.path.join(model_dir, "model.bin")
            model_config = {
                "model_type": job.config.model_type.value,
                "base_model": job.config.base_model,
                "training_config": {
                    "learning_rate": job.config.learning_rate,
                    "batch_size": job.config.batch_size,
                    "num_epochs": job.config.num_epochs
                },
                "training_data_size": len(training_data),
                "final_loss": job.training_loss[-1] if job.training_loss else 0.0
            }
            
            with open(model_path, 'w') as f:
                json.dump(model_config, f, indent=2)
            
            return model_dir
            
        except Exception as e:
            self.logger.error(f"Error running training: {e}")
            return None
    
    async def _evaluate_trained_model(self, job: TrainingJob) -> Optional[ModelEvaluation]:
        """Evaluate a trained model."""
        try:
            evaluation = ModelEvaluation(
                evaluation_id=f"eval_{job.job_id}",
                model_id=job.job_id,  # Use job_id as temporary model_id
                evaluator_id="system"
            )
            
            # Simulate evaluation metrics based on training performance
            if job.training_loss and job.validation_loss:
                final_train_loss = job.training_loss[-1]
                final_val_loss = job.validation_loss[-1]
                
                # Convert loss to accuracy (simplified)
                evaluation.accuracy = max(0.1, 1.0 - final_val_loss / 3.0)
                evaluation.precision = evaluation.accuracy * random.uniform(0.9, 1.1)
                evaluation.recall = evaluation.accuracy * random.uniform(0.9, 1.1)
                evaluation.f1_score = 2 * (evaluation.precision * evaluation.recall) / (evaluation.precision + evaluation.recall)
                evaluation.perplexity = max(1.1, final_val_loss * 2.0)
                
                if job.config.model_type in [ModelType.SUMMARIZATION, ModelType.LANGUAGE_MODEL]:
                    evaluation.bleu_score = max(0.1, evaluation.accuracy * random.uniform(0.8, 1.2))
            
            evaluation.test_samples = min(1000, len(job.training_logs))
            evaluation.evaluation_time = random.uniform(30.0, 300.0)  # Simulate evaluation time
            
            return evaluation
            
        except Exception as e:
            self.logger.error(f"Error evaluating trained model: {e}")
            return None
    
    async def _register_trained_model(self, job: TrainingJob) -> str:
        """Register a trained model in the model registry."""
        try:
            model_id = f"model_{job.job_id}_{datetime.now().timestamp()}"
            
            # Calculate model size (simplified)
            model_size_mb = random.uniform(10.0, 500.0)
            model_parameters = int(model_size_mb * 1000000 / 4)  # Rough estimate
            
            model_info = {
                "model_id": model_id,
                "name": job.model_name,
                "description": job.description,
                "type": job.config.model_type.value,
                "base_model": job.config.base_model,
                "training_job_id": job.job_id,
                "created_at": datetime.now().isoformat(),
                "model_path": job.model_path,
                "size_mb": model_size_mb,
                "parameters": model_parameters,
                "training_config": {
                    "learning_rate": job.config.learning_rate,
                    "batch_size": job.config.batch_size,
                    "num_epochs": job.config.num_epochs,
                    "max_sequence_length": job.config.max_sequence_length
                },
                "datasets_used": job.dataset_ids,
                "training_duration_hours": job.get_duration(),
                "deployed": False
            }
            
            # Add evaluation results if available
            if job.evaluation_results:
                latest_eval = job.evaluation_results[-1]
                model_info["latest_evaluation"] = latest_eval.get_overall_score()
                model_info["evaluation_metrics"] = {
                    "accuracy": latest_eval.accuracy,
                    "f1_score": latest_eval.f1_score,
                    "perplexity": latest_eval.perplexity
                }
            
            self.trained_models[model_id] = model_info
            
            return model_id
            
        except Exception as e:
            self.logger.error(f"Error registering trained model: {e}")
            return ""
    
    async def _prepare_evaluation_data(self, dataset_ids: List[str]) -> List[Dict[str, Any]]:
        """Prepare evaluation data from datasets."""
        try:
            eval_data = []
            
            for dataset_id in dataset_ids:
                entries = await self._get_dataset_entries(dataset_id)
                
                # Take a sample for evaluation
                sample_size = min(self.config["evaluation_samples"], len(entries))
                sample_entries = random.sample(entries, sample_size)
                
                for entry in sample_entries:
                    eval_sample = {
                        "input": entry.title,
                        "expected_output": entry.content,
                        "category": entry.category.value,
                        "quality": entry.quality_score
                    }
                    eval_data.append(eval_sample)
            
            return eval_data
            
        except Exception as e:
            self.logger.error(f"Error preparing evaluation data: {e}")
            return []
    
    async def _get_default_test_data(self, model_id: str) -> List[Dict[str, Any]]:
        """Get default test data for a model."""
        try:
            # In a real implementation, this would retrieve test data used during training
            # For now, return empty list
            return []
            
        except Exception as e:
            self.logger.error(f"Error getting default test data: {e}")
            return []
    
    async def _run_model_evaluation(
        self,
        model_info: Dict[str, Any],
        test_data: List[Dict[str, Any]],
        custom_metrics: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Run evaluation on a model."""
        try:
            # Simulate model evaluation
            # In a real implementation, this would load and run the actual model
            
            results = {
                "accuracy": random.uniform(0.6, 0.95),
                "precision": random.uniform(0.6, 0.95),
                "recall": random.uniform(0.6, 0.95),
                "f1_score": 0.0,  # Will be calculated
                "perplexity": random.uniform(1.5, 4.0),
                "bleu_score": random.uniform(0.3, 0.8),
                "custom_metrics": custom_metrics or {}
            }
            
            # Calculate F1 score
            if results["precision"] > 0 and results["recall"] > 0:
                results["f1_score"] = 2 * (results["precision"] * results["recall"]) / (results["precision"] + results["recall"])
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error running model evaluation: {e}")
            return {}
    
    async def _job_monitor(self) -> None:
        """Background task to monitor training jobs."""
        while True:
            try:
                await asyncio.sleep(300)  # Check every 5 minutes
                
                current_time = datetime.now()
                
                for job in self.training_jobs.values():
                    # Check for timeouts
                    if (job.status in [TrainingStatus.TRAINING, TrainingStatus.PREPARING] and
                        job.started_at and
                        (current_time - job.started_at).total_seconds() / 3600.0 > job.config.max_training_time_hours):
                        
                        job.status = TrainingStatus.FAILED
                        job.error_message = "Training timeout exceeded"
                        job.completed_at = current_time
                        job.add_log("Training job timed out")
                        
                        self.active_jobs.discard(job.job_id)
                        self.stats["failed_jobs"] += 1
                        
                        self.logger.warning(f"Training job {job.job_id} timed out")
                
            except Exception as e:
                self.logger.error(f"Error in job monitor: {e}")
                await asyncio.sleep(60)
    
    async def _cleanup_processor(self) -> None:
        """Background task to clean up old training data and models."""
        while True:
            try:
                await asyncio.sleep(86400)  # Run daily
                
                cutoff_date = datetime.now() - timedelta(days=self.config["checkpoint_retention_days"])
                
                # Clean up old checkpoints and temporary files
                training_dir = os.path.join(self.config["model_registry_path"], "training")
                if os.path.exists(training_dir):
                    for job_dir in os.listdir(training_dir):
                        job_path = os.path.join(training_dir, job_dir)
                        if os.path.isdir(job_path):
                            # Check if job is old and completed/failed
                            job_id = job_dir
                            if job_id in self.training_jobs:
                                job = self.training_jobs[job_id]
                                if (job.status in [TrainingStatus.COMPLETED, TrainingStatus.FAILED, TrainingStatus.CANCELLED] and
                                    job.completed_at and job.completed_at < cutoff_date):
                                    
                                    # Remove training directory
                                    shutil.rmtree(job_path, ignore_errors=True)
                                    self.logger.info(f"Cleaned up old training data for job {job_id}")
                
            except Exception as e:
                self.logger.error(f"Error in cleanup processor: {e}")
                await asyncio.sleep(3600)
    
    async def _save_training_state(self) -> None:
        """Save training state to persistent storage."""
        try:
            # In a real implementation, this would save to database or files
            self.logger.info(f"Saved training state: {len(self.training_jobs)} jobs, {len(self.trained_models)} models")
        except Exception as e:
            self.logger.error(f"Error saving training state: {e}")