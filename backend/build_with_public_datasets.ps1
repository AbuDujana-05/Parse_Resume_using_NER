$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
python .\download_public_datasets.py
python .\prepare_data.py
python .\train_antigravity.py
