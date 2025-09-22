pgrep run_playwright.sh | xargs kill -s 9

nohup run_playwright.sh > run.log 2>&1 &