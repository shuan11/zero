
import subprocess, time, sys, os
WATCHED = ['meta_gap_finder', 'co_evolution_daemon']
while True:
    ps = subprocess.run(['ps','aux'], capture_output=True, text=True).stdout
    for name in WATCHED:
        if name not in ps:
            os.system(f'cd /mnt/c/Users/h/Desktop/零/真元集群 && nohup python3 {name}.py > /tmp/{name}.log 2>&1 &')
    time.sleep(30)
