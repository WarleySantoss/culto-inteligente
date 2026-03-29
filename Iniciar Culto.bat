@echo off
title Motor do Culto Inteligente
echo ==========================================
echo    INICIANDO O SISTEMA CULTO INTELIGENTE
echo ==========================================
echo Ligando o banco de dados e a Inteligencia Artificial...
echo.

:: Ativa o seu ambiente virtual silenciosamente
call .venv\Scripts\activate

:: Roda o seu aplicativo
python main.py

exit