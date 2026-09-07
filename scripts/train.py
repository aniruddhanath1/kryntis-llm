"""
Standalone script to train the model from scratch.
Usage: python scripts/train.py [--resume]
"""

import sys
from kryntis.training.trainer import Trainer

if __name__ == "__main__":
    resume = "--resume" in sys.argv
    print(f"Starting Kryntis Coder Pretraining (resume={resume})...")
    trainer = Trainer()
    trainer.train(resume=resume)
