"""
STUB engine file. Replace with the real calibrator trainer.

Expected CLI:
    python train_weather_commitment_calibrator.py --version <id>
Outputs: a path on stdout to the new calibrator artifact.
"""
import argparse
import sys
import time


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", type=str, required=True)
    args = ap.parse_args()

    # Pretend to train.
    time.sleep(0.2)
    artifact = f"/tmp/calibrator-{args.version}.bin"
    with open(artifact, "wb") as f:
        f.write(b"\x00" * 8)
    print(artifact)


if __name__ == "__main__":
    main()
