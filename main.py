"""
Water Margin Story (水滸傳: 천명의 맹세)
A crewAI strategy game — defeat Gao Qiu before the Song dynasty falls.
"""

from __future__ import annotations

import os
from dotenv import load_dotenv

load_dotenv()

from game.engine import GameEngine
from ui.terminal_ui import TerminalUI


def main() -> None:
    ui = TerminalUI()
    engine = GameEngine(ui=ui)
    engine.run()


if __name__ == "__main__":
    main()
