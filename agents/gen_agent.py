from __future__ import annotations

from schema.asset import AssetOutput
from schema.asset_gen import GeneratedAssetOutput

from mcp_tools.asset_generation.executor import (
    AssetExecutor
)



class GenerationAgent:

    async def generate(
        self,
        asset_output: AssetOutput
    ) -> GeneratedAssetOutput:
        
        executor = AssetExecutor()

        await executor.connect()


        try:

            result = await executor.execute_assets_output(
                asset_output.assets
            )

            executor.storage.save_generated_assets_output(
                result
            )

            return result

        finally:

            await executor.close()
