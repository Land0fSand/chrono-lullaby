#!/usr/bin/env pwsh
# ChronoLullaby 统一命令入口
# 此脚本会将所有命令转发到 scripts/ch.ps1

$scriptDir = Split-Path $MyInvocation.MyCommand.Path -Parent
& "$scriptDir\scripts\ch.ps1" @args

