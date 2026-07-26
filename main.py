#!/usr/bin/env python3
"""botyaragames - Mini Games Hub"""

import sys
import os

# Ensure working directory is script directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))

import pygame
from core.engine import Engine


def main():
    pygame.init()
    engine = Engine()
    engine.run()
    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()