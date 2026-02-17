from abc import ABC, abstractmethod

class BaseStrategy(ABC):
    """
    Abstract base class for all trading strategies.
    Enforces a consistent interface for starting, stopping, and handling market events.
    """

    @abstractmethod
    def start(self) -> None:
        """Start the strategy execution loop."""
        pass

    @abstractmethod
    def stop(self) -> None:
        """Stop the strategy execution loop."""
        pass

    @property
    @abstractmethod
    def is_running(self) -> bool:
        """Check if the strategy is currently active."""
        pass
