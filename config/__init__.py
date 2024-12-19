import pandas as pd
import pathlib

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib


config_path = pathlib.Path(__file__).parent / "config.toml"
with config_path.open(mode="rb") as fp:
    config = tomllib.load(fp)

rig_path = pathlib.Path(__file__).parent / f"rig_{config['test_rig']}.toml"
with rig_path.open(mode="rb") as fp:
    rig = tomllib.load(fp)

try:
    path_loss_path = pathlib.Path(__file__).parent / config["path_loss_file"]
    path_loss = pd.read_csv(path_loss_path, index_col="frequency")
except:
    path_loss_path = None
    path_loss = None
