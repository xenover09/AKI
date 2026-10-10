import json
import logging
import traceback
from typing import Optional
from permissions import check_permission, PermissionTier
from tools.browser_tool import BrowserTool

logger = logging.getLogger("ai_engine.agent")

class Agent:
    def __init__(self, ai_service, log_callback=None):
        self.ai_service = ai_service
        self.browser = BrowserTool()
        self.log_callback = log_callback or (lambda msg: logger.info(msg))
        
    def _log(self, message: str):
        self.log_callback(message)

    def run(self, task: str) -> str:
        self._log(f"Starting task: {task}")
        history = [{"role": "user", "content": f"Task: {task}\nYou have access to browser tools: goto, click, type_text, screenshot, read_text. Output exactly one JSON object per step with 'action', 'params' (dict), and 'reasoning'. Max 15 steps. When done, output action='report' with 'text' param."}]
        
        for step in range(15):
            self._log(f"Step {step+1}: Thinking...")
            
            # Simulated LLM call using ai_service. In a real scenario, we pass history.
            try:
                # We expect the AI service to return a JSON string
                response_text = self.ai_service.generate(history)
                # Ensure we extract just the JSON part
                start_idx = response_text.find('{')
                end_idx = response_text.rfind('}')
                if start_idx == -1 or end_idx == -1:
                    raise ValueError("No JSON object found in response.")
                
                step_data = json.loads(response_text[start_idx:end_idx+1])
                action = step_data.get("action")
                params = step_data.get("params", {})
                reasoning = step_data.get("reasoning", "")
                
                self._log(f"Action: {action} | Reasoning: {reasoning}")
                history.append({"role": "assistant", "content": json.dumps(step_data)})
                
                if action == "report":
                    self._log(f"Task completed: {params.get('text')}")
                    return params.get("text", "Done")
                
                # Check permissions
                tier = PermissionTier.SENSITIVE
                if action in ["read_text", "screenshot"]:
                    tier = PermissionTier.SAFE
                elif action in ["goto", "click", "type_text"]:
                    tier = PermissionTier.SENSITIVE
                
                if not check_permission(tier, f"{action} with params: {params}"):
                    self._log(f"Permission denied for {action}")
                    history.append({"role": "user", "content": "Permission denied for that action."})
                    continue
                
                # Execute action
                result = {}
                if action == "goto":
                    result = self.browser.goto(params.get("url", ""))
                elif action == "click":
                    result = self.browser.click(params.get("selector", ""))
                elif action == "type_text":
                    result = self.browser.type_text(params.get("selector", ""), params.get("text", ""))
                elif action == "read_text":
                    result = self.browser.read_text()
                elif action == "screenshot":
                    result = self.browser.screenshot(params.get("path", "screenshot.png"))
                else:
                    result = {"status": "error", "message": f"Unknown action: {action}"}
                
                self._log(f"Result: {result}")
                history.append({"role": "user", "content": json.dumps(result)})
                
            except Exception as e:
                self._log(f"Error during step: {e}")
                history.append({"role": "user", "content": f"Error: {e}"})
                
        self._log("Max steps reached.")
        return "Task failed: Max steps reached."
