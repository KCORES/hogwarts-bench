"""
Sampling strategies for selecting text positions from novels.

This module provides different sampling strategies to select positions
in a tokenized novel for question generation.
"""

import random
from abc import ABC, abstractmethod
from math import ceil
from typing import List


class SamplingStrategy(ABC):
    """Abstract base class for sampling strategies."""
    
    @abstractmethod
    def sample(self, total_tokens: int, num_samples: int) -> List[int]:
        """
        Sample positions from the novel.
        
        Args:
            total_tokens: Total number of tokens in the novel
            num_samples: Number of positions to sample
            
        Returns:
            List of token positions, sorted in ascending order
        """
        pass


class StratifiedSampling(SamplingStrategy):
    """
    Stratified sampling strategy that divides the novel into layers
    and samples uniformly from each layer.
    """
    
    def __init__(self, layer_size: int = 50000):
        """
        Initialize stratified sampling.
        
        Args:
            layer_size: Size of each layer in tokens (default: 50000)
        """
        self.layer_size = layer_size
    
    def sample(self, total_tokens: int, num_samples: int) -> List[int]:
        """
        Sample positions using stratified sampling.
        
        Divides the novel into layers of fixed token size and samples
        uniformly from each layer to ensure coverage across the entire text.
        
        Args:
            total_tokens: Total number of tokens in the novel
            num_samples: Number of positions to sample
            
        Returns:
            List of token positions, sorted in ascending order
        """
        if total_tokens <= 0:
            return []
        
        if num_samples <= 0:
            return []
        
        # Calculate number of layers
        num_layers = ceil(total_tokens / self.layer_size)
        
        # Calculate samples per layer
        samples_per_layer = num_samples // num_layers
        remaining_samples = num_samples % num_layers
        
        positions = []
        
        for layer_idx in range(num_layers):
            layer_start = layer_idx * self.layer_size
            layer_end = min((layer_idx + 1) * self.layer_size, total_tokens)
            
            # Calculate how many samples for this layer
            layer_samples = samples_per_layer
            if layer_idx < remaining_samples:
                layer_samples += 1
            
            # Sample uniformly within layer
            if layer_end > layer_start:
                for _ in range(layer_samples):
                    pos = random.randint(layer_start, layer_end - 1)
                    positions.append(pos)
        
        return sorted(positions)


class RandomSampling(SamplingStrategy):
    """
    Random sampling strategy that selects positions uniformly
    across the entire novel.
    """
    
    def sample(self, total_tokens: int, num_samples: int) -> List[int]:
        """
        Sample positions using random sampling.
        
        Selects positions uniformly at random from the entire novel.
        
        Args:
            total_tokens: Total number of tokens in the novel
            num_samples: Number of positions to sample
            
        Returns:
            List of token positions, sorted in ascending order
        """
        if total_tokens <= 0:
            return []
        
        if num_samples <= 0:
            return []
        
        # Ensure we don't try to sample more than available
        num_samples = min(num_samples, total_tokens)
        
        # Sample random positions
        positions = random.sample(range(total_tokens), num_samples)
        
        return sorted(positions)


def get_sampling_strategy(strategy_name: str, **kwargs) -> SamplingStrategy:
    """
    Factory function to get a sampling strategy by name.
    
    Args:
        strategy_name: Name of the strategy ("stratified" or "random")
        **kwargs: Additional arguments to pass to the strategy constructor
        
    Returns:
        An instance of the requested sampling strategy
        
    Raises:
        ValueError: If strategy_name is not recognized
    """
    strategies = {
        "stratified": StratifiedSampling,
        "random": RandomSampling,
    }
    
    strategy_name_lower = strategy_name.lower()
    
    if strategy_name_lower not in strategies:
        raise ValueError(
            f"Unknown sampling strategy: {strategy_name}. "
            f"Available strategies: {', '.join(strategies.keys())}"
        )
    
    return strategies[strategy_name_lower](**kwargs)
