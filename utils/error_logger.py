"""
Error logging utility for the RAG demo application.
This module provides functions to log and track errors that occur during API calls,
particularly when dealing with rate limits and quota issues.
"""

import os
import json
import time
import datetime
from collections import defaultdict


class APIErrorTracker:
    """Tracks API errors, especially rate limits, to help with troubleshooting."""
    
    def __init__(self, log_dir="./logs"):
        self.log_dir = log_dir
        self.error_counts = defaultdict(int)
        self.last_error_time = defaultdict(float)
        self.success_counts = defaultdict(int)
        
        # Create log directory if it doesn't exist
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
    
    def log_error(self, error_type, details, api_type="openai"):
        """Log an API error with details."""
        self.error_counts[error_type] += 1
        self.last_error_time[error_type] = time.time()
        
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = {
            "timestamp": timestamp,
            "api_type": api_type,
            "error_type": error_type,
            "details": str(details),
            "count": self.error_counts[error_type]
        }
        
        # Write to daily log file
        date_str = datetime.datetime.now().strftime("%Y-%m-%d")
        log_filename = f"{self.log_dir}/{api_type}_errors_{date_str}.log"
        
        with open(log_filename, "a") as f:
            f.write(json.dumps(log_entry) + "\n")
        
        return log_entry
    
    def log_success(self, operation_type, api_type="openai"):
        """Log a successful API operation."""
        self.success_counts[operation_type] += 1
    
    def get_error_summary(self):
        """Get a summary of errors that have occurred."""
        summary = {
            "total_errors": sum(self.error_counts.values()),
            "error_types": dict(self.error_counts),
            "success_counts": dict(self.success_counts),
        }
        
        # Add time since last error for each type
        current_time = time.time()
        time_since_last = {}
        for error_type, last_time in self.last_error_time.items():
            if last_time > 0:
                time_since_last[error_type] = round(current_time - last_time, 2)
        
        summary["time_since_last_error"] = time_since_last
        return summary
    
    def should_continue(self, error_type, threshold=5, window_seconds=300):
        """
        Determine if operations should continue based on error frequency.
        
        Args:
            error_type: The type of error to check
            threshold: Maximum number of errors allowed in the time window
            window_seconds: Time window in seconds to check
            
        Returns:
            bool: True if operations should continue, False if they should stop
        """
        # If we haven't seen this error type yet, continue
        if error_type not in self.error_counts:
            return True
            
        # If we're under the threshold, continue
        if self.error_counts[error_type] < threshold:
            return True
            
        # Check if we're outside the time window since the last error
        current_time = time.time()
        time_since_last = current_time - self.last_error_time[error_type]
        
        # If enough time has passed since the last error, reset the counter and continue
        if time_since_last > window_seconds:
            self.error_counts[error_type] = 0
            return True
            
        # We're hitting errors too frequently, suggest pausing
        return False


# Create a global instance for use throughout the application
error_tracker = APIErrorTracker()


def get_error_tracker():
    """Get the global error tracker instance."""
    return error_tracker
