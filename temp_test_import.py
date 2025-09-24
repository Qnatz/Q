import sys
sys.path.append('/root/Q')

from utils.ui_helpers import say_error

try:
    say_error("Test error message from temp_test_import.py")
    print("say_error function called successfully.")
except NameError as e:
    print(f"NameError: {e}")
except Exception as e:
    print(f"An unexpected error occurred: {e}")
