@echo off
setlocal
title English Video Player - Recuperacao V2.9.8

echo ==============================================
echo English Video Player - Recuperacao V2.9.8
echo ==============================================
echo.
echo Este reparo atualiza apenas os arquivos necessarios
echo para recuperar a inicializacao da V2.9.7.
echo Seus dados, biblioteca e progresso nao serao apagados.
echo.

set "REPAIR_URL=https://raw.githubusercontent.com/janduyankiingles-ops/App-Ingl-s-/7f953e065d1d18179ffdc71c1f5ae721f9ba4075/repair_v298.py"
set "REPAIR_FILE=%TEMP%\english_video_player_repair_v298.py"

echo Baixando reparador validado...
powershell -NoProfile -ExecutionPolicy Bypass -Command "Invoke-WebRequest -UseBasicParsing '%REPAIR_URL%' -OutFile '%REPAIR_FILE%'"
if errorlevel 1 goto download_error

echo.
echo Executando reparo...
where py >nul 2>nul
if not errorlevel 1 (
    py -3 "%REPAIR_FILE%"
    goto finished
)

where python >nul 2>nul
if not errorlevel 1 (
    python "%REPAIR_FILE%"
    goto finished
)

echo.
echo ERRO: Python nao foi encontrado no PATH.
echo Abra a pasta do English Video Player e execute repair_v298.py manualmente.
goto end

:download_error
echo.
echo ERRO: Nao foi possivel baixar o reparador.
echo Verifique sua conexao com a internet.
goto end

:finished
echo.
echo Processo de recuperacao finalizado.

:end
echo.
pause
endlocal
