"""Entry point for the SHPE Capital web GUI."""
from src.web.app import launch_web_gui

if __name__ == '__main__':
    launch_web_gui(debug=True)
