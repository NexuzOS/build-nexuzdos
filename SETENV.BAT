@echo off
echo Setting up system to build MS-DOS 4.01...

:: 1. Zuerst die Basis definieren!
set BAKROOT=D:

:: 2. Variablen initialisieren
set CL=
set LINK=
set MASM=

:: 3. Pfade setzen (Nutze BAKROOT erst NACHDEM es oben gesetzt wurde)
set COUNTRY=usa-ms
set LIB=%BAKROOT%\src\tools\bld\lib
set INIT=%BAKROOT%\src\tools
set INCLUDE=%BAKROOT%\src\tools\bld\inc

:: 4. PATH optimieren
:: WICHTIG: Die Tools müssen ZUERST im Pfad stehen. 
:: Vermeide zu viele Ordner im Pfad (DOS-Limit!), meist reichen die Tools.
set PATH=%BAKROOT%\src\tools;%BAKROOT%\src\tools\bld;%BAKROOT%\src\messages;%BAKROOT%\src\mapper;%BAKROOT%\src\memm;%BAKROOT%\src\bios;%BAKROOT%\src\boot;%BAKROOT%\src\dos;%BAKROOT%\src\dev;%BAKROOT%\src\cmd;%BAKROOT%\src\h;%BAKROOT%\src\select;%BAKROOT%\src\LIB;%BAKROOT%\src\INC;%PATH%

echo Environment ready. BAKROOT is %BAKROOT%