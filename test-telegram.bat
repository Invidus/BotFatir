@echo off
echo Testing api.telegram.org ...
curl -s -o NUL -w "HTTP %%{http_code}, time %%{time_total}s\n" --connect-timeout 10 https://api.telegram.org
if errorlevel 1 (
    echo FAILED - Telegram API is not reachable from this PC.
    echo Try: enable VPN, or add HTTP_PROXY to .env
) else (
    echo OK - Telegram API is reachable.
)
pause
