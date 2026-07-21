import os
import re

with open("main.py", "r", encoding="utf-8") as f:
    content = f.read()

endpoints = """
import urllib.parse
import httpx
import aiofiles
from fastapi import UploadFile, File

@app.get("/design-sessions/{session_id}/assets/plan")
async def get_asset_plan(session_id: str):
    from agents.asset_agent import AssetAgent
    agent = AssetAgent()
    assets = agent._scan_code_for_assets()
    return {"assets": [a.model_dump() for a in assets]}

class GenerateAssetRequest(BaseModel):
    prompt: str
    width: int
    height: int

@app.post("/design-sessions/{session_id}/assets/{asset_id}/generate")
async def generate_single_asset(session_id: str, asset_id: str, request: GenerateAssetRequest):
    encoded_prompt = urllib.parse.quote(request.prompt)
    url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={request.width}&height={request.height}&nologo=true"
    
    os.makedirs(GENERATED_ASSETS_DIR, exist_ok=True)
    filepath = os.path.join(GENERATED_ASSETS_DIR, f"{asset_id}.png")
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url, timeout=60.0)
        response.raise_for_status()
        async with aiofiles.open(filepath, "wb") as f:
            await f.write(response.content)
            
    return {"asset_id": asset_id, "url": f"/generated-assets/{asset_id}.png"}

@app.post("/design-sessions/{session_id}/assets/{asset_id}/upload")
async def upload_single_asset(session_id: str, asset_id: str, file: UploadFile = File(...)):
    os.makedirs(GENERATED_ASSETS_DIR, exist_ok=True)
    filepath = os.path.join(GENERATED_ASSETS_DIR, f"{asset_id}.png") # Save as png so injection agent finds it easily
    
    async with aiofiles.open(filepath, "wb") as f:
        content = await file.read()
        await f.write(content)
        
    return {"asset_id": asset_id, "url": f"/generated-assets/{asset_id}.png"}

class InjectAssetConfig(BaseModel):
    asset_id: str
    is_parallax: bool
    
class InjectAssetsRequest(BaseModel):
    assets: list[InjectAssetConfig]

@app.post("/design-sessions/{session_id}/assets/inject")
async def inject_assets_endpoint(session_id: str, request: InjectAssetsRequest):
    from agents.asset_injection_agent import AssetInjectionAgent
    agent = AssetInjectionAgent()
    
    # We pass the user configs to the injection agent
    # Since inject_assets doesn't take args currently, we write a temporary config file for it
    config_path = os.path.join(GENERATED_ASSETS_DIR, "injection_config.json")
    os.makedirs(GENERATED_ASSETS_DIR, exist_ok=True)
    with open(config_path, "w", encoding="utf-8") as f:
        f.write(request.model_dump_json())
        
    await agent.inject_assets() 
    
    ensure_generated_site_entrypoints()
    normalize_generated_package_json()
    build_generated_site()
    
    session = _get_design_session(session_id)
    session["status"] = "completed"
    
    return {"status": "ok"}
"""

if "@app.get(\"/design-sessions/{session_id}/assets/plan\")" not in content:
    content = content.replace("frontend_dist = ", endpoints + "\n\nfrontend_dist = ")
    with open("main.py", "w", encoding="utf-8") as f:
        f.write(content)
    print("Added endpoints successfully.")
else:
    print("Endpoints already exist.")
