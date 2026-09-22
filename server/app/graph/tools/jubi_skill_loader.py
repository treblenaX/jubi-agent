"""
Jubi Skill Loader for Jubi Agent

This module provides skill loading functionality for Jubi's researcher agent.
It reads SKILL.md files from /home/ec/.nanobot/workspace/jubi/researcher/skills/ and
converts them to executable Python skills that can be used by the researcher agent.

Note: Jubi is standalone and does not depend on nanobot at all.
"""

import os
import sys
import json
import re
from typing import Dict, List, Optional, Any, Callable
from abc import ABC, abstractmethod


class JubiSkill(ABC):
    """Abstract base class for Jubi skills."""
    
    def __init__(self, name: str, description: str, category: str = "jubi"):
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


class GrillSkill(JubiSkill):
    """Structured questioning skill for Jubi."""

    def __init__(self):
        super().__init__(
            name="grill",
            description="Structured questioning to reach shared understanding before action. "
                        "Asks ONE question at a time, checks memory for prior decisions.",
            category="questioning"
        )

    def execute(self, query: str, **kwargs) -> Dict[str, Any]:
        """Execute grill skill - asks structured questions."""
        return {
            "skill": self.name,
            "query": query,
            "status": "questioning",
            "message": f"Asking structured questions for: {query}"
        }


class RubberDuckSkill(JubiSkill):
    """Rubber duck skill from Jubi."""

    def __init__(self, explanation: str = None, original_ask: str = None):
        super().__init__(
            name="rubber-duck",
            description="Adversarial review that catches hallucinations and gaps. "
                        "Spawns a subagent listener that interrogates your reasoning.",
            category="verification"
        )
        self.explanation = explanation or ""
        self.original_ask = original_ask or ""

    def execute(self, query: str, **kwargs) -> Dict[str, Any]:
        """Execute rubber duck skill - spawns listener for adversarial review."""
        return {
            "skill": self.name,
            "query": query,
            "status": "reviewing",
            "message": f"Starting adversarial review of: {query}",
            "listener_task": f"Review this explanation:\n{self.explanation}\n\nOriginal ask: {self.original_ask}"
        }


class GoalLoopSkill(JubiSkill):
    """Goal management skill from Jubi."""
    
    def __init__(self):
        super().__init__(
            name="goal-loop",
            description="Manage sustained goals for long-running sessions. "
                        "Creates bounded objectives with explicit completion criteria.",
            category="management"
        )
    
    def execute(self, query: str, action: str = "create", **kwargs) -> Dict[str, Any]:
        """Execute goal loop skill."""
        return {
            "skill": self.name,
            "query": query,
            "action": action,
            "status": "managed",
            "message": f"Goal action '{action}' executed for: {query}"
        }


class TaskDecompositionSkill(JubiSkill):
    """Task decomposition skill from Jubi."""
    
    def __init__(self):
        super().__init__(
            name="task-decomposition",
            description="Decomposes complex tasks into atomic units for worker agents. "
                        "Breaks down work, establishes dependencies, assigns to workers.",
            category="orchestration"
        )
    
    def execute(self, query: str, **kwargs) -> Dict[str, Any]:
        """Execute task decomposition skill."""
        return {
            "skill": self.name,
            "query": query,
            "status": "decomposed",
            "message": f"Decomposing task: {query}",
            "subtasks": ["Analyze requirements", "Define atomic units", "Establish dependencies", "Assign to workers"]
        }


class StateManagementSkill(JubiSkill):
    """State management skill from Jubi."""
    
    def __init__(self):
        super().__init__(
            name="state-management",
            description="Manages agent states, task progress, and workspace artifacts. "
                        "Tracks task completion, manages shared workspace.",
            category="management"
        )
    
    def execute(self, query: str, action: str = "track", **kwargs) -> Dict[str, Any]:
        """Execute state management skill."""
        return {
            "skill": self.name,
            "query": query,
            "action": action,
            "status": "managed",
            "message": f"State action '{action}' executed for: {query}"
        }


class VerificationSkill(JubiSkill):
    """Verification skill from Jubi."""
    
    def __init__(self):
        super().__init__(
            name="verification",
            description="Validates outputs from worker agents, ensures quality standards. "
                        "Reports on task completion in Jubi's Evaluator-Optimizer pattern.",
            category="evaluation"
        )
    
    def execute(self, query: str, **kwargs) -> Dict[str, Any]:
        """Execute verification skill."""
        return {
            "skill": self.name,
            "query": query,
            "status": "verified",
            "message": f"Verifying: {query}",
            "quality_check": "Checking against quality standards..."
        }


class ContextIsolationSkill(JubiSkill):
    """Context isolation skill from Jubi."""

    def __init__(self):
        super().__init__(
            name="context-isolation",
            description="Manages context isolation for subagents. "
                        "Prevents context pollution, manages token budgets.",
            category="optimization"
        )

    def execute(self, query: str, **kwargs) -> Dict[str, Any]:
        """Execute context isolation skill."""
        return {
            "skill": self.name,
            "query": query,
            "status": "isolated",
            "message": f"Context isolated for: {query}",
            "token_budget": kwargs.get("budget", "default")
        }


class TokenEfficiencySkill(JubiSkill):
    """Token efficiency skill from Jubi."""

    def __init__(self):
        super().__init__(
            name="token-efficiency",
            description="Optimizes token usage across agents. "
                        "Prunes context, selects appropriate models, manages budgets.",
            category="optimization"
        )

    def execute(self, query: str, **kwargs) -> Dict[str, Any]:
        """Execute token efficiency skill."""
        return {
            "skill": self.name,
            "query": query,
            "status": "optimized",
            "message": f"Optimizing tokens for: {query}",
            "savings": kwargs.get("estimated_savings", "unknown")
        }


class GatewayRestartSkill(JubiSkill):
    """Gateway restart skill from Jubi."""

    def __init__(self):
        super().__init__(
            name="gateway-restart",
            description="Safely restart the nanobot gateway. "
                        "Handles restarts for different install types.",
            category="maintenance"
        )

    def execute(self, query: str, **kwargs) -> Dict[str, Any]:
        """Execute gateway restart skill."""
        return {
            "skill": self.name,
            "query": query,
            "status": "restarting",
            "message": f"Restarting gateway for: {query}"
        }


class SelfUpdateSkill(JubiSkill):
    """Self-update skill from Jubi."""

    def __init__(self):
        super().__init__(
            name="self-update",
            description="Check for and apply nanobot updates. "
                        "Checks PyPI/npm registry, applies updates.",
            category="maintenance"
        )

    def execute(self, query: str, **kwargs) -> Dict[str, Any]:
        """Execute self-update skill."""
        return {
            "skill": self.name,
            "query": query,
            "status": "checking",
            "message": f"Checking for updates: {query}"
        }


class DiscordFormattingSkill(JubiSkill):
    """Discord formatting skill from Jubi."""

    def __init__(self):
        super().__init__(
            name="discord-formatting",
            description="Mobile-friendly Discord message formatting with tables, "
                        "diagrams, and ANSI colors.",
            category="formatting"
        )

    def execute(self, query: str, **kwargs) -> Dict[str, Any]:
        """Execute discord formatting skill."""
        return {
            "skill": self.name,
            "query": query,
            "status": "formatted",
            "message": f"Formatting for Discord: {query}"
        }


class UsingSuperpowersSkill(JubiSkill):
    """Using superpowers skill from Jubi."""

    def __init__(self):
        super().__init__(
            name="using-superpowers",
            description="Use when starting any conversation - establishes how to "
                        "find and use skills, requiring skill invocation before ANY response.",
            category="guidance"
        )

    def execute(self, query: str, **kwargs) -> Dict[str, Any]:
        """Execute using superpowers skill."""
        return {
            "skill": self.name,
            "query": query,
            "status": "guided",
            "message": f"Using superpowers for: {query}"
        }


class SpecDrivenDevelopmentSkill(JubiSkill):
    """Spec-driven development skill from Jubi."""

    def __init__(self):
        super().__init__(
            name="spec-driven-development",
            description="Builds software using specifications as the primary source of truth. "
                        "Creates testable contracts, validates implementations.",
            category="development"
        )

    def execute(self, query: str, **kwargs) -> Dict[str, Any]:
        """Execute spec-driven development skill."""
        return {
            "skill": self.name,
            "query": query,
            "status": "specifying",
            "message": f"Applying spec-driven development for: {query}"
        }


class TddSkill(JubiSkill):
    """TDD skill from Jubi."""

    def __init__(self):
        super().__init__(
            name="tdd",
            description="Test-driven development. Write tests first, then implementation.",
            category="development"
        )

    def execute(self, query: str, **kwargs) -> Dict[str, Any]:
        """Execute TDD skill."""
        return {
            "skill": self.name,
            "query": query,
            "status": "tdd",
            "message": f"Applying TDD for: {query}"
        }


class MemorySkill(JubiSkill):
    """Memory skill from Jubi."""

    def __init__(self):
        super().__init__(
            name="memory",
            description="Search past conversations in the agent's history log.",
            category="knowledge"
        )

    def execute(self, query: str, **kwargs) -> Dict[str, Any]:
        """Execute memory skill."""
        return {
            "skill": self.name,
            "query": query,
            "status": "searching",
            "message": f"Searching memory for: {query}"
        }


class ImageGenerationSkill(JubiSkill):
    """Image generation skill from Jubi."""

    def __init__(self):
        super().__init__(
            name="image-generation",
            description="Generate images and iteratively edit saved image artifacts.",
            category="creative"
        )

    def execute(self, query: str, **kwargs) -> Dict[str, Any]:
        """Execute image generation skill."""
        return {
            "skill": self.name,
            "query": query,
            "status": "generating",
            "message": f"Generating image for: {query}"
        }


class SummarizeSkill(JubiSkill):
    """Summarize skill from Jubi."""

    def __init__(self):
        super().__init__(
            name="summarize",
            description="Summarize or extract text/transcripts from URLs, podcasts, and local files.",
            category="knowledge"
        )

    def execute(self, query: str, **kwargs) -> Dict[str, Any]:
        """Execute summarize skill."""
        return {
            "skill": self.name,
            "query": query,
            "status": "summarizing",
            "message": f"Summarizing: {query}"
        }


class CronSkill(JubiSkill):
    """Cron skill from Jubi."""

    def __init__(self):
        super().__init__(
            name="cron",
            description="Schedule reminders and recurring tasks.",
            category="automation"
        )

    def execute(self, query: str, **kwargs) -> Dict[str, Any]:
        """Execute cron skill."""
        return {
            "skill": self.name,
            "query": query,
            "status": "scheduled",
            "message": f"Scheduling task for: {query}"
        }


class GithubSkill(JubiSkill):
    """GitHub skill from Jubi."""

    def __init__(self):
        super().__init__(
            name="github",
            description="Interact with GitHub using the gh CLI.",
            category="devops"
        )

    def execute(self, query: str, **kwargs) -> Dict[str, Any]:
        """Execute github skill."""
        return {
            "skill": self.name,
            "query": query,
            "status": "github",
            "message": f"GitHub action for: {query}"
        }


class WeatherSkill(JubiSkill):
    """Weather skill from Jubi."""

    def __init__(self):
        super().__init__(
            name="weather",
            description="Get current weather and forecasts (no API key required).",
            category="utility"
        )

    def execute(self, query: str, **kwargs) -> Dict[str, Any]:
        """Execute weather skill."""
        return {
            "skill": self.name,
            "query": query,
            "status": "checking",
            "message": f"Checking weather for: {query}"
        }


class SkillRegistry:
    """
    Registry for managing skills loaded into Jubi.

    Provides dynamic skill loading from SKILL.md files in the Jubi skills directory.
    Skills can be loaded automatically or programmatically.
    """

    def __init__(self):
        self._skills: Dict[str, JubiSkill] = {}
        # Jubi skills directory only - no nanobot dependency
        self._jubi_skill_dir = "/home/ec/.nanobot/workspace/jubi/researcher/skills"
    
    def _load_skill_from_markdown(self, skill_name: str) -> Optional[JubiSkill]:
        """Load a skill from its SKILL.md file."""
        # Load from Jubi skills directory only
        skill_path = os.path.join(self._jubi_skill_dir, skill_name, "SKILL.md")
        
        if not os.path.exists(skill_path):
            return None
        
        try:
            with open(skill_path, 'r') as f:
                content = f.read()
            
            # Extract YAML frontmatter
            frontmatter_end = content.find("---\n\n", content.find("---"))
            if frontmatter_end == -1:
                return None
            
            frontmatter = content[:frontmatter_end + 4]
            body = content[frontmatter_end + 4:]
            
            # Parse simple YAML
            data = {}
            for line in frontmatter.strip().split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    data[key.strip()] = value.strip()
            
            description = data.get("description", f"Skill: {skill_name}")
            always = data.get("always", "false").lower() == "true"
            triggers = [t.strip() for t in data.get("triggers", "").split(",")]
            
            # Create appropriate skill instance based on name
            skill_map = {
                "grill": GrillSkill,
                "rubber-duck": lambda: RubberDuckSkill(),
                "goal-loop": GoalLoopSkill,
                "task-decomposition": TaskDecompositionSkill,
                "state-management": StateManagementSkill,
                "verification": VerificationSkill,
                "context-isolation": ContextIsolationSkill,
                "token-efficiency": TokenEfficiencySkill,
                "gateway-restart": lambda: GatewayRestartSkill(),
                "self-update": lambda: SelfUpdateSkill(),
                "discord-formatting": lambda: DiscordFormattingSkill(),
                "using-superpowers": lambda: UsingSuperpowersSkill(),
                "spec-driven-development": lambda: SpecDrivenDevelopmentSkill(),
                "tdd": lambda: TddSkill(),
                "memory": lambda: MemorySkill(),
                "image-generation": lambda: ImageGenerationSkill(),
                "summarize": lambda: SummarizeSkill(),
                "cron": lambda: CronSkill(),
                "github": lambda: GithubSkill(),
                "weather": lambda: WeatherSkill(),
            }

            skill_class = skill_map.get(skill_name.lower())
            if skill_class:
                return skill_class()

            # Default to a generic skill for unknown skills
            return JubiSkill(
                name=skill_name,
                description=description,
                category="jubi"
            )
            
        except Exception as e:
            print(f"Failed to load skill {skill_name}: {e}")
            return None
    
    def load_all_skills(self) -> int:
        """Load all skills from Jubi skills directory."""
        loaded = 0

        # Load from Jubi skills directory only
        for filename in os.listdir(self._jubi_skill_dir):
            if filename.endswith("/"):
                continue

            skill_path = os.path.join(self._jubi_skill_dir, filename)

            if os.path.isdir(skill_path):
                # Try to load from SKILL.md
                skill = self._load_skill_from_markdown(filename)
                if skill:
                    self.register(skill)
                    loaded += 1

        return loaded
    
    def register(self, skill: JubiSkill) -> None:
        """Register a skill by name."""
        if skill.name in self._skills:
            # Skip duplicate registration
            return
        self._skills[skill.name] = skill
    
    def unregister(self, name: str) -> bool:
        """Unregister a skill by name."""
        if name in self._skills:
            del self._skills[name]
            return True
        return False
    
    def get(self, name: str) -> Optional[JubiSkill]:
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
        """Load skills from a Python module."""
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location("skill_module", module_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            loaded_count = 0
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if isinstance(attr, JubiSkill):
                    self.register(attr)
                    loaded_count += 1
            
            return loaded_count
            
        except Exception as e:
            print(f"Failed to load skills from {module_path}: {e}")
            return 0
    
    def discover_skills(self, skills_dir: str) -> int:
        """Discover and load all .py files in a skills directory."""
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
            "jubi_skills_dir": self._jubi_skill_dir
        }
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def load_registry(self, path: str) -> int:
        """Load registry state from JSON."""
        try:
            with open(path, 'r') as f:
                data = json.load(f)
            
            # Restore skill directories from saved config
            if "jubi_skills_dir" in data:
                self._jubi_skill_dir = data["jubi_skills_dir"]
            if "nanobot_skills_dir" in data:
                self._nanobot_skill_dir = data["nanobot_skills_dir"]
            
            for skill_data in data.get("skills", []):
                name = skill_data["name"]
                description = skill_data.get("description", "")
                category = skill_data.get("category", "nanobot")
                
                # Reconstruct appropriate skill instance - explicit instantiation to avoid closure issues
                if category == "grill":
                    skill = GrillSkill()
                elif category == "rubber-duck":
                    skill = RubberDuckSkill()
                elif category == "goal-loop":
                    skill = GoalLoopSkill()
                elif category == "task-decomposition":
                    skill = TaskDecompositionSkill()
                elif category == "state-management":
                    skill = StateManagementSkill()
                elif category == "verification":
                    skill = VerificationSkill()
                elif category == "context-isolation":
                    skill = ContextIsolationSkill()
                elif category == "token-efficiency":
                    skill = TokenEfficiencySkill()
                elif category == "gateway-restart":
                    skill = GatewayRestartSkill()
                elif category == "self-update":
                    skill = SelfUpdateSkill()
                elif category == "discord-formatting":
                    skill = DiscordFormattingSkill()
                elif category == "using-superpowers":
                    skill = UsingSuperpowersSkill()
                elif category == "spec-driven-development":
                    skill = SpecDrivenDevelopmentSkill()
                elif category == "tdd":
                    skill = TddSkill()
                elif category == "memory":
                    skill = MemorySkill()
                elif category == "image-generation":
                    skill = ImageGenerationSkill()
                elif category == "summarize":
                    skill = SummarizeSkill()
                elif category == "cron":
                    skill = CronSkill()
                elif category == "github":
                    skill = GithubSkill()
                elif category == "weather":
                    skill = WeatherSkill()
                else:
                    skill = JubiSkill(name=name, description=description, category="nanobot")
                    skill.name = name
                    skill.description = description
                    self.register(skill)
            
            return len(self._skills)
            
        except Exception as e:
            print(f"Failed to load registry from {path}: {e}")
            return 0


# Default skills registry (singleton) - auto-load on first access
_default_registry = None


def get_registry() -> SkillRegistry:
    """Get the default skill registry, loading skills if not already loaded."""
    global _default_registry
    if _default_registry is None:
        _default_registry = SkillRegistry()
        _default_registry.load_all_skills()
    return _default_registry


def register_skill(skill: JubiSkill) -> None:
    """Register a skill with the default registry."""
    get_registry().register(skill)


def execute_skill(name: str, query: str, **kwargs) -> Optional[Dict[str, Any]]:
    """Execute a skill from the default registry."""
    return get_registry().execute(name, query, **kwargs)


def list_skills(category: Optional[str] = None) -> List[Dict[str, Any]]:
    """List skills from the default registry."""
    return get_registry().list_skills(category)
