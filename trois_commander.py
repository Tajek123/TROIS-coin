#!/usr/bin/env python3
import os
import subprocess
import time
import sys
import signal
import json

# --- CONFIGURATION ---
USER_HOME = os.path.expanduser("~")
COIN_DIR = os.path.join(USER_HOME, ".troiscoin")
BIN_DIR = os.path.join(USER_HOME, "troiscoin/src") # Adjust if your src is elsewhere
DAEMON = os.path.join(BIN_DIR, "bitcoind")
CLI = os.path.join(BIN_DIR, "bitcoin-cli")
WALLET_NAME = "FirstPersonal"
MINING_ADDRESS = "bc1qcr2a3lm8cv9lfwy64hfuqm36hukg7xxtv57tx7" # Hardcoded for safety

# --- COLORS ---
C_GREEN = '\033[92m'
C_RED = '\033[91m'
C_YELLOW = '\033[93m'
C_BLUE = '\033[94m'
C_RESET = '\033[0m'

def clear_screen():
    os.system('clear')

def print_header():
    clear_screen()
    print(f"{C_BLUE}========================================{C_RESET}")
    print(f"{C_BLUE}      TROIS COIN (ISC) COMMANDER       {C_RESET}")
    print(f"{C_BLUE}========================================{C_RESET}")

def run_command(args, as_json=False):
    """Runs a bitcoin-cli command and returns output."""
    cmd = [CLI, "-datadir=" + COIN_DIR] + args
    try:
        result = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
        output = result.decode('utf-8').strip()
        if as_json:
            try:
                return json.loads(output)
            except:
                return output
        return output
    except subprocess.CalledProcessError as e:
        return f"ERROR: {e.output.decode('utf-8').strip()}"
    except FileNotFoundError:
        return "ERROR: Binary not found. Check paths."

def check_status():
    """Checks if the daemon is running."""
    try:
        # Grep for bitcoind process
        output = subprocess.check_output(["pidof", "bitcoind"])
        return True
    except:
        return False

def start_node():
    print(f"{C_YELLOW}Starting TROIS Daemon...{C_RESET}")
    try:
        subprocess.Popen([DAEMON, "-datadir=" + COIN_DIR, "-daemon"])
        print("Waiting for initialization (30s)...")
        time.sleep(30)
        # Auto load wallet
        run_command(["loadwallet", WALLET_NAME])
        print(f"{C_GREEN}Node Started!{C_RESET}")
    except Exception as e:
        print(f"{C_RED}Failed to start: {e}{C_RESET}")
    input("Press Enter...")

def stop_node():
    print(f"{C_YELLOW}Stopping Daemon...{C_RESET}")
    print(run_command(["stop"]))
    time.sleep(5)
    input("Press Enter...")

def view_wallet():
    print_header()
    if not check_status():
        print(f"{C_RED}Node is not running! Start it first.{C_RESET}")
        input("Press Enter...")
        return

    print(f"Target Wallet: {WALLET_NAME}")
    print("--------------------------------")
    
    # Get Balance
    bal = run_command(["-rpcwallet=" + WALLET_NAME, "getbalance"])
    # Get Immature Balance
    all_bal = run_command(["-rpcwallet=" + WALLET_NAME, "getbalances"], as_json=True)
    immature = "0.00"
    if isinstance(all_bal, dict) and "mine" in all_bal:
        immature = all_bal["mine"].get("immature", 0)

    print(f"{C_GREEN}Trusted Balance : {bal} ISC{C_RESET}")
    print(f"{C_YELLOW}Immature Balance: {immature} ISC{C_RESET}")
    print("--------------------------------")
    
    print("1. Get New Address")
    print("2. Dump Private Key (Requires Unlock)")
    print("3. Back")
    
    choice = input("Select: ")
    if choice == "1":
        addr = run_command(["-rpcwallet=" + WALLET_NAME, "getnewaddress"])
        print(f"New Address: {addr}")
        input("Press Enter...")
    elif choice == "2":
        addr = input("Enter Address to dump key for: ")
        pw = input("Enter Wallet Password (will show text): ")
        # Unlock
        run_command(["-rpcwallet=" + WALLET_NAME, "walletpassphrase", pw, "60"])
        key = run_command(["-rpcwallet=" + WALLET_NAME, "dumpprivkey", addr])
        print(f"{C_RED}PRIVATE KEY: {key}{C_RESET}")
        # Lock
        run_command(["-rpcwallet=" + WALLET_NAME, "walletlock"])
        input("Press Enter...")

def miner_menu():
    while True:
        print_header()
        print(f"Mining Address: {MINING_ADDRESS}")
        print("--------------------------------")
        print("1. Mine ONE Block (Test)")
        print("2. Infinite Mine (Foreground - Ctrl+C to stop)")
        print("3. Start Background Miner (Silent)")
        print("4. Stop Background Miner")
        print("5. Back")
        
        choice = input("Select: ")
        
        if choice == "1":
            print("Mining...")
            res = run_command(["-rpcwallet=" + WALLET_NAME, "generatetoaddress", "1", MINING_ADDRESS, "999999999"])
            print(res)
            input("Press Enter...")
            
        elif choice == "2":
            print(f"{C_GREEN}Starting Infinite Miner. Press Ctrl+C to stop.{C_RESET}")
            blocks_found = 0
            try:
                while True:
                    # We use 1 million tries
                    res = run_command(["-rpcwallet=" + WALLET_NAME, "generatetoaddress", "1", MINING_ADDRESS, "1000000"])
                    
                    # FIX: Only count as success if there is a quote " symbol in the result
                    if '"' in res:
                        blocks_found += 1
                        print(f"\n{C_GREEN}🚀 BLOCK FOUND! Total this session: {blocks_found}{C_RESET}")
                        print(res)
                    else:
                        print(".", end="", flush=True)
            except KeyboardInterrupt:
                print("\nMining stopped.")
                
        elif choice == "3":
            # Create a separate python script for bg mining on the fly
            with open("bg_miner.py", "w") as f:
                f.write(f"""
import subprocess, time
cmd = ["{CLI}", "-datadir={COIN_DIR}", "-rpcwallet={WALLET_NAME}", "generatetoaddress", "1", "{MINING_ADDRESS}", "1000000"]
while True:
    subprocess.call(cmd)
    time.sleep(1)
""")
            subprocess.Popen(["python3", "bg_miner.py"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print(f"{C_GREEN}Background Miner Started! Check top/htop to verify.{C_RESET}")
            input("Press Enter...")
            
        elif choice == "4":
            os.system("pkill -f bg_miner.py")
            print(f"{C_RED}Background Miner Killed.{C_RESET}")
            input("Press Enter...")
            
        elif choice == "5":
            break

# --- MAIN LOOP ---
while True:
    print_header()
    
    if check_status():
        status_text = f"{C_GREEN}RUNNING{C_RESET}"
        # Get Block Count
        height = run_command(["getblockcount"])
    else:
        status_text = f"{C_RED}STOPPED{C_RESET}"
        height = "?"
        
    print(f"Daemon Status: {status_text}")
    print(f"Block Height : {height}")
    print("--------------------------------")
    print("1. Start Node")
    print("2. Stop Node")
    print("3. Wallet & Keys")
    print("4. MINING OPERATIONS")
    print("5. Exit")
    
    choice = input("Select option: ")
    
    if choice == "1":
        start_node()
    elif choice == "2":
        stop_node()
    elif choice == "3":
        view_wallet()
    elif choice == "4":
        if check_status():
            miner_menu()
        else:
            print("Start the node first!")
            time.sleep(1)
    elif choice == "5":
        print("Goodbye.")
        sys.exit()
