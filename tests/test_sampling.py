"""Tests for sampling strategies."""

import pytest
from src.generator.sampling import (
    StratifiedSampling,
    RandomSampling,
    get_sampling_strategy,
)


class TestStratifiedSampling:
    """Tests for stratified sampling strategy."""
    
    def test_stratified_sampling_basic(self):
        """Test basic stratified sampling."""
        strategy = StratifiedSampling(layer_size=50000)
        positions = strategy.sample(total_tokens=100000, num_samples=10)
        
        assert len(positions) == 10
        assert all(0 <= pos < 100000 for pos in positions)
        assert positions == sorted(positions)  # Should be sorted
    
    def test_stratified_sampling_distribution(self):
        """Test that stratified sampling distributes across layers."""
        strategy = StratifiedSampling(layer_size=50000)
        positions = strategy.sample(total_tokens=150000, num_samples=30)
        
        # Should have 3 layers (0-50k, 50k-100k, 100k-150k)
        layer1 = [p for p in positions if p < 50000]
        layer2 = [p for p in positions if 50000 <= p < 100000]
        layer3 = [p for p in positions if 100000 <= p < 150000]
        
        # Each layer should have approximately equal samples
        assert len(layer1) == 10
        assert len(layer2) == 10
        assert len(layer3) == 10
    
    def test_stratified_sampling_empty(self):
        """Test stratified sampling with zero samples."""
        strategy = StratifiedSampling()
        positions = strategy.sample(total_tokens=100000, num_samples=0)
        
        assert len(positions) == 0
    
    def test_stratified_sampling_zero_tokens(self):
        """Test stratified sampling with zero tokens."""
        strategy = StratifiedSampling()
        positions = strategy.sample(total_tokens=0, num_samples=10)
        
        assert len(positions) == 0
    
    def test_stratified_sampling_small_novel(self):
        """Test stratified sampling with novel smaller than layer size."""
        strategy = StratifiedSampling(layer_size=50000)
        positions = strategy.sample(total_tokens=10000, num_samples=5)
        
        assert len(positions) == 5
        assert all(0 <= pos < 10000 for pos in positions)
        assert positions == sorted(positions)


class TestRandomSampling:
    """Tests for random sampling strategy."""
    
    def test_random_sampling_basic(self):
        """Test basic random sampling."""
        strategy = RandomSampling()
        positions = strategy.sample(total_tokens=100000, num_samples=10)
        
        assert len(positions) == 10
        assert all(0 <= pos < 100000 for pos in positions)
        assert positions == sorted(positions)  # Should be sorted
    
    def test_random_sampling_unique(self):
        """Test that random sampling produces unique positions."""
        strategy = RandomSampling()
        positions = strategy.sample(total_tokens=100000, num_samples=50)
        
        assert len(positions) == len(set(positions))  # All unique
    
    def test_random_sampling_empty(self):
        """Test random sampling with zero samples."""
        strategy = RandomSampling()
        positions = strategy.sample(total_tokens=100000, num_samples=0)
        
        assert len(positions) == 0
    
    def test_random_sampling_zero_tokens(self):
        """Test random sampling with zero tokens."""
        strategy = RandomSampling()
        positions = strategy.sample(total_tokens=0, num_samples=10)
        
        assert len(positions) == 0
    
    def test_random_sampling_more_samples_than_tokens(self):
        """Test random sampling when requesting more samples than tokens."""
        strategy = RandomSampling()
        positions = strategy.sample(total_tokens=10, num_samples=20)
        
        # Should only return as many as available
        assert len(positions) == 10
        assert all(0 <= pos < 10 for pos in positions)


class TestGetSamplingStrategy:
    """Tests for the factory function."""
    
    def test_get_stratified_strategy(self):
        """Test getting stratified strategy."""
        strategy = get_sampling_strategy("stratified")
        assert isinstance(strategy, StratifiedSampling)
    
    def test_get_random_strategy(self):
        """Test getting random strategy."""
        strategy = get_sampling_strategy("random")
        assert isinstance(strategy, RandomSampling)
    
    def test_get_strategy_case_insensitive(self):
        """Test that strategy names are case-insensitive."""
        strategy1 = get_sampling_strategy("STRATIFIED")
        strategy2 = get_sampling_strategy("Stratified")
        strategy3 = get_sampling_strategy("stratified")
        
        assert isinstance(strategy1, StratifiedSampling)
        assert isinstance(strategy2, StratifiedSampling)
        assert isinstance(strategy3, StratifiedSampling)
    
    def test_get_strategy_with_kwargs(self):
        """Test passing kwargs to strategy constructor."""
        strategy = get_sampling_strategy("stratified", layer_size=100000)
        assert isinstance(strategy, StratifiedSampling)
        assert strategy.layer_size == 100000
    
    def test_get_unknown_strategy(self):
        """Test that unknown strategy raises ValueError."""
        with pytest.raises(ValueError, match="Unknown sampling strategy"):
            get_sampling_strategy("unknown")
