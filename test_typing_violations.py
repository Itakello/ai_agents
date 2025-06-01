#!/usr/bin/env python3
"""Test file to demonstrate typing violations that should be caught by pre-commit."""

from typing import List, Dict, Optional, Union


def example_function(items: List[str], mapping: Dict[str, int], value: Optional[str]) -> Union[str, int]:
    """Example function with old-style typing that should trigger violations."""
    return "test"
