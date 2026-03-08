"""Tool Agent - Provides access to external tools and utilities."""

import json
import logging
import math
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List

logger = logging.getLogger(__name__)


class ToolAgent:
    """Provides external tool capabilities to the RAG system.

    Includes built-in tools (calculator, date/time, web search, unit converter)
    and supports registration of custom tools.
    """

    def __init__(self):
        self.tools: Dict[str, Callable] = {
            "calculator": self._calculator,
            "datetime": self._get_datetime,
            "web_search": self._web_search,
            "unit_converter": self._unit_converter,
        }

    def register_tool(self, name: str, func: Callable, description: str = "") -> None:
        """Register a custom tool.

        Args:
            name: Unique tool name.
            func: Callable that implements the tool.
            description: Human-readable description.
        """
        self.tools[name] = func
        logger.info("Registered tool: %s - %s", name, description)

    def execute(self, tool_name: str, **kwargs: Any) -> str:
        """Execute a tool by name.

        Args:
            tool_name: Name of the tool to execute.
            **kwargs: Arguments to pass to the tool.

        Returns:
            Tool execution result as a string.
        """
        if tool_name not in self.tools:
            return f"Tool '{tool_name}' not found. Available tools: {list(self.tools.keys())}"

        try:
            result = self.tools[tool_name](**kwargs)
            logger.info("Tool '%s' executed successfully", tool_name)
            return str(result)
        except Exception as e:
            logger.error("Tool '%s' failed: %s", tool_name, e)
            return f"Tool execution error: {e}"

    def list_tools(self) -> List[str]:
        """List available tool names.

        Returns:
            List of registered tool names.
        """
        return list(self.tools.keys())

    @staticmethod
    def _calculator(expression: str = "") -> str:
        """Evaluate a mathematical expression safely.

        Args:
            expression: Math expression to evaluate.

        Returns:
            Calculation result or error message.
        """
        allowed_names = {
            "abs": abs,
            "round": round,
            "min": min,
            "max": max,
            "sum": sum,
            "pow": pow,
            "sqrt": math.sqrt,
            "sin": math.sin,
            "cos": math.cos,
            "tan": math.tan,
            "log": math.log,
            "pi": math.pi,
            "e": math.e,
        }

        try:
            # Only allow safe mathematical operations
            code = compile(expression, "<calculator>", "eval")
            for name in code.co_names:
                if name not in allowed_names:
                    return f"Unsafe operation: {name}"
            result = eval(code, {"__builtins__": {}}, allowed_names)  # noqa: S307
            return str(result)
        except Exception as e:
            return f"Calculation error: {e}"

    @staticmethod
    def _get_datetime() -> str:
        """Get current date and time.

        Returns:
            Current UTC datetime string.
        """
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _web_search(query: str = "") -> str:
        """Search the web using DuckDuckGo Instant Answer API (no API key required).

        Args:
            query: Search query string.

        Returns:
            Search results summary or error message.
        """
        if not query:
            return "No search query provided."

        try:
            encoded_query = urllib.parse.quote_plus(query)
            url = f"https://api.duckduckgo.com/?q={encoded_query}&format=json&no_html=1"
            req = urllib.request.Request(url, headers={"User-Agent": "RAG-Agent/1.0"})
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode())

            results = []
            if data.get("AbstractText"):
                results.append(f"Summary: {data['AbstractText']}")
            if data.get("RelatedTopics"):
                for topic in data["RelatedTopics"][:5]:
                    if isinstance(topic, dict) and "Text" in topic:
                        results.append(topic["Text"])

            if results:
                return "\n".join(results)
            return f"No instant results found for: {query}"
        except urllib.error.URLError as e:
            logger.warning("Web search network error: %s", e)
            return f"Web search failed: network error ({e.reason})"
        except TimeoutError:
            logger.warning("Web search timed out for query: %s", query)
            return "Web search failed: request timed out"
        except Exception as e:
            logger.warning("Web search failed: %s", e)
            return f"Web search unavailable: {e}"

    @staticmethod
    def _unit_converter(value: float = 0, from_unit: str = "", to_unit: str = "") -> str:
        """Convert between common units.

        Args:
            value: Numeric value to convert.
            from_unit: Source unit.
            to_unit: Target unit.

        Returns:
            Converted value or error message.
        """
        conversions = {
            ("km", "miles"): 0.621371,
            ("miles", "km"): 1.60934,
            ("kg", "lbs"): 2.20462,
            ("lbs", "kg"): 0.453592,
            ("c", "f"): lambda v: v * 9 / 5 + 32,
            ("f", "c"): lambda v: (v - 32) * 5 / 9,
            ("m", "ft"): 3.28084,
            ("ft", "m"): 0.3048,
            ("l", "gal"): 0.264172,
            ("gal", "l"): 3.78541,
        }

        key = (from_unit.lower(), to_unit.lower())
        if key not in conversions:
            available = [f"{f}->{t}" for f, t in conversions.keys()]
            return f"Unsupported conversion. Available: {', '.join(available)}"

        factor = conversions[key]
        if callable(factor):
            result = factor(value)
        else:
            result = value * factor

        return f"{value} {from_unit} = {round(result, 4)} {to_unit}"
