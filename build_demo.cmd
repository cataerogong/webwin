pyinstaller -F -c ^
            --hide-console hide-early ^
            --collect-binaries webui ^
            --add-data demo.html:. ^
            demo.py
