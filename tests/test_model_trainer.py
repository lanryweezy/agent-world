"""
Tests for the model training and deployment pipeline.
"""

import pytest
import asyncio
import tempfile
import shutil
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock

from autonomous_ai_ecosystem.knowledge.model_trainer import (
    ModelTrainer,
    TrainingJob,
    TrainingConfig,
    ModelEvaluation,
    ModelType,
    TrainingStatus
)
from autonomous_ai_ecosystem.knowledge.dataset_manager import (
    DatasetManager
)


class TestTrainingConfig:
    """Test the TrainingConfig class."""
    
    def test_config_creation(self):
        """Test creating a training configuration."""
        config = TrainingConfig(
            model_type=ModelType.LANGUAGE_MODEL,
            base_model="gpt2-small",
            learning_rate=1e-4,
            batch_size=16,
            num_epochs=5
        )
        
        assert config.model_type == ModelType.LANGUAGE_MODEL
        assert config.base_model == "gpt2-small"
        assert config.learning_rate == 1e-4
        assert config.batch_size == 16
        assert config.num_epochs == 5
        assert config.train_split == 0.8  # Default value
        assert config.use_gpu is True  # Default value
    
    def test_config_defaults(self):
        """Test default configuration values."""
        config = TrainingConfig(model_type=ModelType.CLASSIFICATION)
        
        assert config.learning_rate == 5e-5
        assert config.batch_size == 8
        assert config.num_epochs == 3
        assert config.max_sequence_length == 512
        assert config.train_split == 0.8
        assert config.validation_split == 0.1
        assert config.test_split == 0.1


class TestModelEvaluation:
    """Test the ModelEvaluation class."""
    
    def test_evaluation_creation(self):
        """Test creating a model evaluation."""
        evaluation = ModelEvaluation(
            evaluation_id="eval_1",
            model_id="model_1",
            evaluator_id="agent_1",
            accuracy=0.85,
            precision=0.82,
            recall=0.88,
            f1_score=0.85
        )
        
        assert evaluation.evaluation_id == "eval_1"
        assert evaluation.model_id == "model_1"
        assert evaluation.evaluator_id == "agent_1"
        assert evaluation.accuracy == 0.85
        assert evaluation.precision == 0.82
        assert evaluation.recall == 0.88
        assert evaluation.f1_score == 0.85
    
    def test_overall_score_calculation(self):
        """Test overall score calculation."""
        evaluation = ModelEvaluation(
            evaluation_id="eval_1",
            model_id="model_1",
            evaluator_id="agent_1",
            accuracy=0.8,
            f1_score=0.75,
            bleu_score=0.7,
            perplexity=2.0
        )
        
        overall_score = evaluation.get_overall_score()
        
        # Should average accuracy, f1_score, bleu_score, and converted perplexity
        expected_perplexity_score = 1.0 / (1.0 + 2.0)  # 0.333...
        expected_score = (0.8 + 0.75 + 0.7 + expected_perplexity_score) / 4
        
        assert abs(overall_score - expected_score) < 0.01
    
    def test_overall_score_with_custom_metrics(self):
        """Test overall score with custom metrics."""
        evaluation = ModelEvaluation(
            evaluation_id="eval_1",
            model_id="model_1",
            evaluator_id="agent_1",
            accuracy=0.8,
            custom_metrics={"coherence": 0.9, "relevance": 0.85}
        )
        
        overall_score = evaluation.get_overall_score()
        
        # Should include custom metrics in the average
        expected_score = (0.8 + 0.9 + 0.85) / 3
        assert abs(overall_score - expected_score) < 0.01


class TestTrainingJob:
    """Test the TrainingJob class."""
    
    def test_job_creation(self):
        """Test creating a training job."""
        config = TrainingConfig(model_type=ModelType.CLASSIFICATION)
        
        job = TrainingJob(
            job_id="job_1",
            initiator_id="agent_1",
            model_name="Test Model",
            description="A test model",
            config=config,
            dataset_ids=["dataset_1", "dataset_2"]
        )
        
        assert job.job_id == "job_1"
        assert job.initiator_id == "agent_1"
        assert job.model_name == "Test Model"
        assert job.config.model_type == ModelType.CLASSIFICATION
        assert len(job.dataset_ids) == 2
        assert job.status == TrainingStatus.QUEUED
        assert job.progress_percentage == 0.0
    
    def test_duration_calculation(self):
        """Test training duration calculation."""
        config = TrainingConfig(model_type=ModelType.LANGUAGE_MODEL)
        job = TrainingJob(
            job_id="job_1",
            initiator_id="agent_1",
            model_name="Test Model",
            description="Test",
            config=config,
            dataset_ids=["dataset_1"]
        )
        
        # No start time
        assert job.get_duration() == 0.0
        
        # With start time
        job.started_at = datetime.now() - timedelta(hours=2)
        duration = job.get_duration()
        assert 1.9 < duration < 2.1  # Approximately 2 hours
        
        # With completion time
        job.completed_at = datetime.now() - timedelta(hours=1)
        duration = job.get_duration()
        assert 0.9 < duration < 1.1  # Approximately 1 hour
    
    def test_add_log(self):
        """Test adding log messages."""
        config = TrainingConfig(model_type=ModelType.LANGUAGE_MODEL)
        job = TrainingJob(
            job_id="job_1",
            initiator_id="agent_1",
            model_name="Test Model",
            description="Test",
            config=config,
            dataset_ids=["dataset_1"]
        )
        
        job.add_log("Training started")
        job.add_log("Epoch 1 completed")
        
        assert len(job.training_logs) == 2
        assert "Training started" in job.training_logs[0]
        assert "Epoch 1 completed" in job.training_logs[1]
        
        # Test log size limit
        for i in range(1005):
            job.add_log(f"Log message {i}")
        
        assert len(job.training_logs) == 1000  # Should be limited


class TestModelTrainer:
    """Test the ModelTrainer class."""
    
    @pytest.fixture
    async def model_trainer(self):
        """Create a test model trainer."""
        # Create temporary directories
        temp_dir = tempfile.mkdtemp()
        dataset_temp_dir = tempfile.mkdtemp()
        
        # Create mock dataset manager
        dataset_manager = Mock(spec=DatasetManager)
        dataset_manager.datasets = {
            "dataset_1": Mock(total_entries=1000),
            "dataset_2": Mock(total_entries=500)
        }
        dataset_manager.knowledge_entries = {}
        
        trainer = ModelTrainer("test_trainer", dataset_manager, temp_dir)
        await trainer.initialize()
        
        yield trainer
        
        # Cleanup
        await trainer.shutdown()
        shutil.rmtree(temp_dir, ignore_errors=True)
        shutil.rmtree(dataset_temp_dir, ignore_errors=True)
    
    @pytest.mark.asyncio
    async def test_trainer_initialization(self):
        """Test model trainer initialization."""
        temp_dir = tempfile.mkdtemp()
        try:
            dataset_manager = Mock(spec=DatasetManager)
            dataset_manager.datasets = {}
            
            trainer = ModelTrainer("test_trainer", dataset_manager, temp_dir)
            await trainer.initialize()
            
            assert len(trainer.training_jobs) == 0
            assert len(trainer.trained_models) == 0
            assert trainer.stats["total_jobs"] == 0
            
            await trainer.shutdown()
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.mark.asyncio
    async def test_submit_training_job(self, model_trainer):
        """Test submitting a training job."""
        result = await model_trainer.submit_training_job(
            initiator_id="agent_1",
            model_name="Test Language Model",
            description="A test language model",
            model_type=ModelType.LANGUAGE_MODEL,
            dataset_ids=["dataset_1", "dataset_2"]
        )
        
        assert result["success"] is True
        assert "job_id" in result
        assert result["status"] == TrainingStatus.QUEUED.value
        assert "estimated_completion" in result
        assert result["total_steps"] > 0
        
        # Check job was stored
        job_id = result["job_id"]
        assert job_id in model_trainer.training_jobs
        
        job = model_trainer.training_jobs[job_id]
        assert job.model_name == "Test Language Model"
        assert job.initiator_id == "agent_1"
        assert job.config.model_type == ModelType.LANGUAGE_MODEL
        assert len(job.dataset_ids) == 2
    
    @pytest.mark.asyncio
    async def test_submit_job_with_custom_config(self, model_trainer):
        """Test submitting a job with custom configuration."""
        config = TrainingConfig(
            model_type=ModelType.CLASSIFICATION,
            learning_rate=1e-4,
            batch_size=16,
            num_epochs=5
        )
        
        result = await model_trainer.submit_training_job(
            initiator_id="agent_1",
            model_name="Custom Model",
            description="Model with custom config",
            model_type=ModelType.CLASSIFICATION,
            dataset_ids=["dataset_1"],
            config=config
        )
        
        assert result["success"] is True
        
        job_id = result["job_id"]
        job = model_trainer.training_jobs[job_id]
        assert job.config.learning_rate == 1e-4
        assert job.config.batch_size == 16
        assert job.config.num_epochs == 5
    
    @pytest.mark.asyncio
    async def test_submit_job_nonexistent_dataset(self, model_trainer):
        """Test submitting job with nonexistent dataset."""
        result = await model_trainer.submit_training_job(
            initiator_id="agent_1",
            model_name="Test Model",
            description="Test",
            model_type=ModelType.LANGUAGE_MODEL,
            dataset_ids=["nonexistent_dataset"]
        )
        
        assert result["success"] is False
        assert "not found" in result["error"]
    
    @pytest.mark.asyncio
    async def test_get_training_job_status(self, model_trainer):
        """Test getting training job status."""
        # Submit a job first
        submit_result = await model_trainer.submit_training_job(
            initiator_id="agent_1",
            model_name="Test Model",
            description="Test",
            model_type=ModelType.LANGUAGE_MODEL,
            dataset_ids=["dataset_1"]
        )
        job_id = submit_result["job_id"]
        
        # Get status
        status = await model_trainer.get_training_job_status(job_id)
        
        assert "job_id" in status
        assert status["job_id"] == job_id
        assert status["model_name"] == "Test Model"
        assert status["status"] == TrainingStatus.QUEUED.value
        assert "progress" in status
        assert "created_at" in status
        assert "duration_hours" in status
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_job_status(self, model_trainer):
        """Test getting status of nonexistent job."""
        status = await model_trainer.get_training_job_status("nonexistent")
        
        assert "error" in status
    
    @pytest.mark.asyncio
    async def test_cancel_training_job(self, model_trainer):
        """Test cancelling a training job."""
        # Submit a job first
        submit_result = await model_trainer.submit_training_job(
            initiator_id="agent_1",
            model_name="Test Model",
            description="Test",
            model_type=ModelType.LANGUAGE_MODEL,
            dataset_ids=["dataset_1"]
        )
        job_id = submit_result["job_id"]
        
        # Cancel the job
        cancel_result = await model_trainer.cancel_training_job(job_id)
        
        assert cancel_result["success"] is True
        assert cancel_result["status"] == TrainingStatus.CANCELLED.value
        
        # Check job status
        job = model_trainer.training_jobs[job_id]
        assert job.status == TrainingStatus.CANCELLED
        assert job.completed_at is not None
    
    @pytest.mark.asyncio
    async def test_cancel_nonexistent_job(self, model_trainer):
        """Test cancelling a nonexistent job."""
        result = await model_trainer.cancel_training_job("nonexistent")
        
        assert result["success"] is False
        assert "not found" in result["error"]
    
    @pytest.mark.asyncio
    async def test_evaluate_model(self, model_trainer):
        """Test evaluating a model."""
        # Add a mock trained model
        model_id = "test_model_1"
        model_trainer.trained_models[model_id] = {
            "model_id": model_id,
            "name": "Test Model",
            "type": ModelType.CLASSIFICATION.value,
            "model_path": "/fake/path"
        }
        
        # Mock the evaluation methods
        with patch.object(model_trainer, '_prepare_evaluation_data', new_callable=AsyncMock) as mock_prep:
            with patch.object(model_trainer, '_run_model_evaluation', new_callable=AsyncMock) as mock_eval:
                mock_prep.return_value = [{"input": "test", "output": "result"}]
                mock_eval.return_value = {
                    "accuracy": 0.85,
                    "precision": 0.82,
                    "recall": 0.88,
                    "f1_score": 0.85
                }
                
                result = await model_trainer.evaluate_model(
                    evaluator_id="agent_1",
                    model_id=model_id,
                    test_dataset_ids=["dataset_1"]
                )
        
        assert result["success"] is True
        assert "evaluation_id" in result
        assert result["overall_score"] > 0
        assert "metrics" in result
        assert result["metrics"]["accuracy"] == 0.85
        
        # Check evaluation was stored
        assert model_id in model_trainer.evaluation_results
        evaluations = model_trainer.evaluation_results[model_id]
        assert len(evaluations) == 1
        assert evaluations[0].evaluator_id == "agent_1"
    
    @pytest.mark.asyncio
    async def test_evaluate_nonexistent_model(self, model_trainer):
        """Test evaluating a nonexistent model."""
        result = await model_trainer.evaluate_model(
            evaluator_id="agent_1",
            model_id="nonexistent",
            test_dataset_ids=["dataset_1"]
        )
        
        assert result["success"] is False
        assert "not found" in result["error"]
    
    @pytest.mark.asyncio
    async def test_deploy_model(self, model_trainer):
        """Test deploying a model."""
        # Add a mock trained model with good evaluation
        model_id = "test_model_1"
        model_trainer.trained_models[model_id] = {
            "model_id": model_id,
            "name": "Test Model",
            "type": ModelType.CLASSIFICATION.value,
            "model_path": "/fake/path",
            "latest_evaluation": 0.9  # Above deployment threshold
        }
        
        result = await model_trainer.deploy_model(
            deployer_id="agent_1",
            model_id=model_id,
            deployment_name="test_deployment"
        )
        
        assert result["success"] is True
        assert "deployment_id" in result
        assert result["deployment_name"] == "test_deployment"
        assert result["status"] == "active"
        
        # Check model info was updated
        model_info = model_trainer.trained_models[model_id]
        assert model_info["deployed"] is True
        assert model_info["deployment_name"] == "test_deployment"
    
    @pytest.mark.asyncio
    async def test_deploy_low_quality_model(self, model_trainer):
        """Test deploying a model with low quality."""
        # Add a mock trained model with poor evaluation
        model_id = "test_model_1"
        model_trainer.trained_models[model_id] = {
            "model_id": model_id,
            "name": "Test Model",
            "type": ModelType.CLASSIFICATION.value,
            "model_path": "/fake/path",
            "latest_evaluation": 0.5  # Below deployment threshold
        }
        
        result = await model_trainer.deploy_model(
            deployer_id="agent_1",
            model_id=model_id,
            deployment_name="test_deployment"
        )
        
        assert result["success"] is False
        assert "below deployment threshold" in result["error"]
    
    def test_get_training_jobs(self, model_trainer):
        """Test getting training jobs."""
        # This test needs to be run after trainer initialization
        asyncio.run(self._test_get_training_jobs_async(model_trainer))
    
    async def _test_get_training_jobs_async(self, model_trainer):
        """Async helper for training jobs test."""
        # Submit some jobs
        await model_trainer.submit_training_job(
            initiator_id="agent_1",
            model_name="Model 1",
            description="First model",
            model_type=ModelType.LANGUAGE_MODEL,
            dataset_ids=["dataset_1"]
        )
        
        await model_trainer.submit_training_job(
            initiator_id="agent_2",
            model_name="Model 2",
            description="Second model",
            model_type=ModelType.CLASSIFICATION,
            dataset_ids=["dataset_2"]
        )
        
        # Get all jobs
        all_jobs = model_trainer.get_training_jobs()
        assert len(all_jobs) == 2
        
        # Get jobs by initiator
        agent1_jobs = model_trainer.get_training_jobs(initiator_id="agent_1")
        assert len(agent1_jobs) == 1
        assert agent1_jobs[0]["model_name"] == "Model 1"
    
    def test_get_trained_models(self, model_trainer):
        """Test getting trained models."""
        # Add some mock models
        model_trainer.trained_models["model_1"] = {
            "model_id": "model_1",
            "name": "Test Model 1",
            "type": ModelType.LANGUAGE_MODEL.value,
            "created_at": "2023-01-01T00:00:00",
            "latest_evaluation": 0.85,
            "deployed": True
        }
        
        model_trainer.trained_models["model_2"] = {
            "model_id": "model_2",
            "name": "Test Model 2",
            "type": ModelType.CLASSIFICATION.value,
            "created_at": "2023-01-02T00:00:00",
            "latest_evaluation": 0.75,
            "deployed": False
        }
        
        models = model_trainer.get_trained_models()
        
        assert len(models) == 2
        assert models[0]["name"] == "Test Model 2"  # More recent first
        assert models[1]["name"] == "Test Model 1"
        assert models[0]["deployed"] is False
        assert models[1]["deployed"] is True
    
    def test_get_model_evaluations(self, model_trainer):
        """Test getting model evaluations."""
        model_id = "test_model"
        
        # Add some mock evaluations
        eval1 = ModelEvaluation(
            evaluation_id="eval_1",
            model_id=model_id,
            evaluator_id="agent_1",
            accuracy=0.8,
            timestamp=datetime.now() - timedelta(hours=2)
        )
        
        eval2 = ModelEvaluation(
            evaluation_id="eval_2",
            model_id=model_id,
            evaluator_id="agent_2",
            accuracy=0.85,
            timestamp=datetime.now() - timedelta(hours=1)
        )
        
        model_trainer.evaluation_results[model_id] = [eval1, eval2]
        
        evaluations = model_trainer.get_model_evaluations(model_id)
        
        assert len(evaluations) == 2
        assert evaluations[0]["evaluation_id"] == "eval_2"  # More recent first
        assert evaluations[1]["evaluation_id"] == "eval_1"
        assert evaluations[0]["metrics"]["accuracy"] == 0.85
    
    def test_get_training_stats(self, model_trainer):
        """Test getting training statistics."""
        # Add some mock data
        model_trainer.stats["total_jobs"] = 10
        model_trainer.stats["completed_jobs"] = 8
        model_trainer.stats["failed_jobs"] = 2
        
        stats = model_trainer.get_training_stats()
        
        assert "total_jobs" in stats
        assert "completed_jobs" in stats
        assert "success_rate_percent" in stats
        assert "job_status_breakdown" in stats
        assert "model_type_breakdown" in stats
        assert "framework_availability" in stats
        
        assert stats["total_jobs"] == 10
        assert stats["completed_jobs"] == 8
        assert stats["success_rate_percent"] == 80.0


if __name__ == "__main__":
    pytest.main([__file__])