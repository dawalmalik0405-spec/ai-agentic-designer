from __future__ import annotations

import os


class CodeStorage:

    def __init__(
        self,
        output_root: str = "generated_sites"
    ):

        self.output_root = output_root

        os.makedirs(
            self.output_root,
            exist_ok=True
        )

    def save_text(
        self,
        content: str,
        filename: str
    ) -> str:

        path = os.path.join(
            self.output_root,
            filename
        )

        with open(
            path,
            "w",
            encoding="utf-8"
        ) as f:

            f.write(content)

        return path
    


