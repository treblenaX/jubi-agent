"""
Researcher Skills System

Provides a modular skills architecture for the researcher agent.
Skills can be dynamically loaded and registered for specialized research operations.

Skill Categories:
- web-research: Advanced web scraping, multi-page analysis
- data-extraction: Structured data parsing from various formats
- comparison: Side-by-side content comparison and synthesis
- monitoring: Continuous monitoring and alerting capabilities
- summarization: Multi-source synthesis and executive summaries
- nanobot: Skills from nanobot's skills library (grill, rubber-duck, goal-loop, etc.)
"""

from typing import Callable, Dict, List, Optional, Any
from abc import ABC, abstractmethod
import json


class BaseSkill(ABC):
    """Abstract base class for all researcher skills."""
    
    def __init__(self, name: str, description: str, category: str):
        self.name = name
        self.description = description
        self.category = category
    
    @abstractmethod
    def execute(self, query: str, **kwargs) -> Dict[str, Any]:
        """Execute the skill with given parameters."""
        pass
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize skill metadata."""
        return {
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "available": True
        }


class WebResearchSkill(BaseSkill):
    """Skills for advanced web research operations."""
    
    def __init__(self, name: str = "web-research", description: str = None):
        super().__init__(
            name=name or "web-research",
            description=description or "Advanced web scraping and multi-page analysis",
            category="web-research"
        )


class DataExtractionSkill(BaseSkill):
    """Skills for structured data extraction."""
    
    def __init__(self, name: str = "data-extraction", description: str = None):
        super().__init__(
            name=name or "data-extraction",
            description=description or "Structured data parsing from various formats",
            category="data-extraction"
        )


class ComparisonSkill(BaseSkill):
    """Skills for content comparison and synthesis."""
    
    def __init__(self, name: str = "comparison", description: str = None):
        super().__init__(
            name=name or "comparison",
            description=description or "Side-by-side content comparison and synthesis",
            category="comparison"
        )


class MonitoringSkill(BaseSkill):
    """Skills for continuous monitoring."""
    
    def __init__(self, name: str = "monitoring", description: str = None):
        super().__init__(
            name=name or "monitoring",
            description=description or "Continuous monitoring and alerting capabilities",
            category="monitoring"
        )


class SummarizationSkill(BaseSkill):
    """Skills for multi-source synthesis."""
    
    def __init__(self, name: str = "summarization", description: str = None):
        super().__init__(
            name=name or "summarization",
            description=description or "Multi-source synthesis and executive summaries",
            category="summarization"
        )


class SkillRegistry:
    """
    Registry for managing researcher skills.
    
    Provides dynamic skill loading, registration, and execution.
    Skills can be loaded from modules, registered programmatically,
    or discovered via a skills directory.
    """
    
    def __init__(self):
        self._skills: Dict[str, BaseSkill] = {}
        self._skill_modules: List[str] = []
    
    def register(self, skill: BaseSkill) -> None:
        """Register a skill by name."""
        if skill.name in self._skills:
            raise ValueError(f"Skill '{skill.name}' already registered")
        self._skills[skill.name] = skill
    
    def unregister(self, name: str) -> bool:
        """Unregister a skill by name."""
        if name in self._skills:
            del self._skills[name]
            return True
        return False
    
    def get(self, name: str) -> Optional[BaseSkill]:
        """Get a skill by name."""
        return self._skills.get(name)
    
    def list_skills(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all registered skills, optionally filtered by category."""
        if category:
            return [s.to_dict() for s in self._skills.values() if s.category == category]
        return [s.to_dict() for s in self._skills.values()]
    
    def execute(self, name: str, query: str, **kwargs) -> Optional[Dict[str, Any]]:
        """Execute a skill by name."""
        skill = self.get(name)
        if skill:
            return skill.execute(query, **kwargs)
        return None
    
    def load_from_module(self, module_path: str) -> int:
        """
        Load skills from a Python module.
        
        Expected module structure:
            - Must define BaseSkill subclasses
            - Each subclass must have an execute() method
            - Module should export skill instances or classes
        
        Returns number of skills loaded.
        """
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location("skill_module", module_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            loaded_count = 0
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if isinstance(attr, BaseSkill):
                    self.register(attr)
                    loaded_count += 1
            
            self._skill_modules.append(module_path)
            return loaded_count
            
        except Exception as e:
            print(f"Failed to load skills from {module_path}: {e}")
            return 0
    
    def discover_skills(self, skills_dir: str) -> int:
        """
        Discover and load all .py files in a skills directory.
        
        Args:
            skills_dir: Path to directory containing skill modules
        
        Returns:
            Number of skills discovered and loaded
        """
        import os
        loaded = 0
        
        for filename in os.listdir(skills_dir):
            if filename.endswith('.py') and not filename.startswith('_'):
                filepath = os.path.join(skills_dir, filename)
                count = self.load_from_module(filepath)
                loaded += count
        
        return loaded
    
    def save_registry(self, path: str) -> None:
        """Save current registry state to JSON."""
        data = {
            "skills": [s.to_dict() for s in self._skills.values()],
            "modules": self._skill_modules
        }
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def load_registry(self, path: str) -> int:
        """Load registry state from JSON."""
        try:
            with open(path, 'r') as f:
                data = json.load(f)
            
            for skill_data in data.get("skills", []):
                # Reconstruct skill instances (simplified - assumes same class names)
                name = skill_data["name"]
                description = skill_data.get("description", "")
                category = skill_data.get("category", "unknown")
                
                if category == "web-research":
                    skill = WebResearchSkill(name, description)
                elif category == "data-extraction":
                    skill = DataExtractionSkill(name, description)
                elif category == "comparison":
                    skill = ComparisonSkill(name, description)
                elif category == "monitoring":
                    skill = MonitoringSkill(name, description)
                elif category == "summarization":
                    skill = SummarizationSkill(name, description)
                else:
                    continue
                
                self.register(skill)
            
            return len(self._skills)
            
        except Exception as e:
            print(f"Failed to load registry from {path}: {e}")
            return 0


# Default skills registry (singleton)
_default_registry = SkillRegistry()


def get_registry() -> SkillRegistry:
    """Get the default skill registry."""
    return _default_registry


def register_skill(skill: BaseSkill) -> None:
    """Register a skill with the default registry."""
    get_registry().register(skill)


def execute_skill(name: str, query: str, **kwargs) -> Optional[Dict[str, Any]]:
    """Execute a skill from the default registry."""
    return get_registry().execute(name, query, **kwargs)


def list_skills(category: Optional[str] = None) -> List[Dict[str, Any]]:
    """List skills from the default registry."""
    return get_registry().list_skills(category)
