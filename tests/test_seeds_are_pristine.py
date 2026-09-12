import subprocess
import sys
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEEDS_DIR = os.path.join(BASE_DIR, 'seeds')

def main():
    if not os.path.exists(SEEDS_DIR):
        print("FAIL: seeds directory not found.")
        sys.exit(1)
        
    try:
        # Use Git as the baseline to ensure seeds haven't been edited.
        output = subprocess.check_output(
            ['git', 'status', '--porcelain', 'seeds/'],
            cwd=BASE_DIR,
            stderr=subprocess.STDOUT
        ).decode('utf-8').strip()
        
        if output:
            print("FAIL: Seeds have been modified!")
            for line in output.split('\n'):
                print(f"  {line}")
            sys.exit(1)
        else:
            print("PASS: Seeds are pristine.")
    except subprocess.CalledProcessError as e:
        print(f"FAIL: Git command failed. {e}")
        sys.exit(1)
    except FileNotFoundError:
        print("FAIL: Git executable not found.")
        sys.exit(1)

if __name__ == "__main__":
    main()
