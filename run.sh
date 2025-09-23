source venv/bin/activate

pgrep run_playwright.sh | xargs kill -s 9

nohup python3 server.py > run.log 2>&1 &