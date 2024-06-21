Write-Host "Export the conda environment..."
conda env export --no-builds | Select-String -Pattern "^prefix: " -NotMatch | Set-Content -Path environment.yml

Write-Host "Export the conda environment..."
pip freeze | Set-Content -Path requirements.txt

Write-Host "Environment export completed."