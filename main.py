import os
import sys

# Add the project root to the Python path
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

if __name__ == "__main__":
    # Run the Streamlit dashboard
    os.system("streamlit run ui/dashboard.py")