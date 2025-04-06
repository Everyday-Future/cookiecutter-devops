# core/adapters/parsers/enum.py

import enum
from typing import Any, Dict, Type, Optional, TypeVar

T = TypeVar('T', bound='StrEnum')


class EnumRegistryMeta(enum.EnumMeta):
    """
    Metaclass that automatically registers all Enum subclasses.

    Maintains a global registry of all enum types that inherit from either
    Enum or StrEnum. The registry is used by JsonSerializer for automatic
    serialization/deserialization without requiring explicit registration.
    """
    _registry: Dict[str, Type] = {}

    def __new__(mcs, name, bases, namespace):
        # Create the enum class
        cls = super().__new__(mcs, name, bases, namespace)
        # Register it globally
        mcs._registry[name] = cls
        return cls

    @classmethod
    def get_registry(mcs) -> Dict[str, Type]:
        """Get the complete registry of enum classes."""
        return mcs._registry

    @classmethod
    def clear_registry(mcs) -> None:
        """Clear the enum registry (mainly for testing)."""
        mcs._registry.clear()


class StrEnum(str, enum.Enum, metaclass=EnumRegistryMeta):
    """
    A string enum that can be used interchangeably as an enum or string.

    Features:
    - String comparison support
    - Format string support
    - Case-insensitive lookup
    - Automatic registration for serialization
    """

    def __str__(self) -> str:
        """Return enum value as string."""
        return self.value

    def __repr__(self) -> str:
        """Developer string representation."""
        return f"{self.__class__.__name__}.{self.name}"

    @classmethod
    def _missing_(cls: Type[T], value: object) -> Optional[T]:
        """Support case-insensitive lookup."""
        if isinstance(value, str):
            # Try case-insensitive match
            value_lower = value.lower()
            for member in cls.__members__.values():
                if member.value.lower() == value_lower:  # Compare with lowercased value
                    return member
        return None

    def __eq__(self, other: Any) -> bool:
        """
        Enhanced equality check that implements:
        - Regular enum equality
        - Case-sensitive string equality
        - Case-insensitive string equality
        """
        if isinstance(other, str):
            return self.value.lower() == other.lower()
        return super().__eq__(other)

    def __hash__(self) -> int:
        """Hash based on the string value."""
        return hash(self.value)


def validate_registry():
    """Helper function to validate registry contents"""
    print("\nRegistry validation:")
    registry = EnumRegistryMeta.get_registry()
    print(f"Current registry contents: {list(registry.keys())}")
    for name, cls in registry.items():
        print(f"- {name}: {cls}")
        print(f"  Members: {[m.name for m in cls]}")
    return registry
