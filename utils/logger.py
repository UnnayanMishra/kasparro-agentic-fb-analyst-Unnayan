"""Structured logging utility."""

import logging
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict


class StructuredLogger:
    """JSON structured logger for agent system."""
    
    def __init__(self, log_file: str = None, level: str = "INFO"):
        self.logger = logging.getLogger("agentic_system")
        self.logger.setLevel(getattr(logging, level.upper()))
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)
        
        # File handler for JSON logs
        if log_file:
            Path(log_file).parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(logging.DEBUG)
            self.logger.addHandler(file_handler)
            
        self.run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.logs = []
        
    def log_agent_execution(
        self,
        agent_name: str,
        event_type: str,
        data: Dict[str, Any],
        status: str = "success"
    ):
        """Log agent execution event."""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "run_id": self.run_id,
            "agent": agent_name,
            "event_type": event_type,
            "status": status,
            "data": data
        }
        
        self.logs.append(log_entry)
        
        # Also log to standard logger
        self.logger.info(f"[{agent_name}] {event_type}: {status}")
        
    def save_logs(self, output_path: str):
        """Save all logs to JSON file."""
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(self.logs, f, indent=2)
        
        self.logger.info(f"Logs saved to {output_path}")
        
    def get_logs(self) -> list:
        """Return all logged events."""
        return self.logs
