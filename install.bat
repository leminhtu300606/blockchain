@echo off
echo ========================================
echo    Blockchain Project - Installation
echo ========================================
echo.

echo Installing required Python packages...
echo.

pip install bit==0.8.0
pip install cryptography==41.0.2
pip install ecdsa==0.18.0
pip install base58
pip install flask
pip install flask-cors

echo.
echo ========================================
echo    Installation Complete!
echo ========================================
pause
