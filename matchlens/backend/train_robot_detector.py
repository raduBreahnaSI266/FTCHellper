import argparse
import shutil
import tempfile
import zipfile
from pathlib import Path


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train a local FTC robot detector from MatchLens YOLO labels.")
    parser.add_argument("dataset_zip", type=Path, help="Dataset ZIP exported from MatchLens")
    parser.add_argument("base_weights", type=Path, help="Existing local YOLO .pt checkpoint; no download is attempted")
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--device", default="auto", help="auto, cpu, or a local GPU index such as 0")
    return parser.parse_args()


def main() -> None:
    args = parse_arguments()
    if not args.dataset_zip.is_file():
        raise SystemExit(f"Dataset ZIP not found: {args.dataset_zip}")
    if not args.base_weights.is_file():
        raise SystemExit(f"Local base weights not found: {args.base_weights}")
    if not 1 <= args.epochs <= 1000:
        raise SystemExit("--epochs must be between 1 and 1000")
    if not 320 <= args.imgsz <= 1280:
        raise SystemExit("--imgsz must be between 320 and 1280")

    try:
        from ultralytics import YOLO
    except ImportError as error:
        raise SystemExit("Install optional training dependencies with: python -m pip install -r requirements-vision.txt") from error

    with tempfile.TemporaryDirectory(prefix="matchlens-training-") as temporary_directory:
        dataset_dir = Path(temporary_directory) / "dataset"
        with zipfile.ZipFile(args.dataset_zip) as archive:
            archive.extractall(dataset_dir)
        dataset_yaml = dataset_dir / "dataset.yaml"
        train_images = dataset_dir / "images" / "train"
        if not dataset_yaml.is_file() or not train_images.is_dir() or not any(train_images.glob("*.jpg")):
            raise SystemExit("Dataset ZIP must contain dataset.yaml and at least one labeled training frame.")

        project_dir = Path(__file__).resolve().parent / "local-models"
        model = YOLO(str(args.base_weights.resolve()))
        result = model.train(
            data=str(dataset_yaml),
            epochs=args.epochs,
            imgsz=args.imgsz,
            project=str(project_dir),
            name="robot-detector-training",
            exist_ok=True,
            workers=0,
            device=None if args.device == "auto" else args.device,
        )
        save_dir = Path(result.save_dir)
        best_weights = save_dir / "weights" / "best.pt"
        if not best_weights.is_file():
            raise SystemExit(f"Training finished but best.pt was not found in {best_weights}")
        destination = project_dir / "robot_detector.pt"
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(best_weights, destination)
        print(f"Trained detector saved to: {destination}")
        print("Set ROBOT_DETECTOR_MODEL=./local-models/robot_detector.pt and ROBOT_DETECTOR_CLASSES=robot in backend/.env, then restart the API.")


if __name__ == "__main__":
    main()