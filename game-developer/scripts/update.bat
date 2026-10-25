@echo off
rem One line on purpose: the installer may rewrite this folder while it runs.
node "%~dp0update.mjs" %* & exit /b
