import json
from pydantic import BaseModel, Field
from agents.llm import qwen_llm
from langchain_core.messages import SystemMessage, HumanMessage

class RevisedPromptResponse(BaseModel):
    revised_prompt: str = Field(..., description="The rewritten prompt incorporating the user's edit request while keeping the core subject intact.")

class AssetAgent:
    """Agent responsible for intelligent asset generation and editing."""
    
    def __init__(self):
        self.llm = qwen_llm()
        
    async def process_edit_request(self, original_prompt: str, edit_request: str) -> str:
        """
        Takes the original image prompt and a user's edit request (e.g., 'make it darker'),
        and rewrites the prompt to apply the edit.
        """
        system_prompt = (
            "You are an expert AI image prompt engineer. Your job is to take an original image prompt "
            "and a user's requested edit, and rewrite the prompt so that it applies the edit seamlessly. "
            "Keep the core subject and style intact unless the edit specifically requests changing them. "
            "Return ONLY the revised prompt as a plain string, optimizing it for text-to-image models."
        )
        
        user_message = (
            f"Original Prompt: {original_prompt}\n"
            f"User's Edit Request: {edit_request}\n\n"
            f"Rewrite the prompt to apply this edit."
        )
        
        try:
            llm_with_structure = self.llm.with_structured_output(RevisedPromptResponse)
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_message)
            ]
            response = await llm_with_structure.ainvoke(messages)
            return response.revised_prompt
        except Exception as e:
            print(f"AssetAgent edit failed: {e}")
            # Fallback to just appending the request if generation fails
            return f"{original_prompt}, {edit_request}"
