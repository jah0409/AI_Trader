from pynput import mouse

def on_click(x, y, button, pressed):
    if pressed:
        print(f"CLICKED -> X: {x}, Y: {y}  (button: {button})")

print("Coordinate Finder started. Click anywhere on your screen.")
print("Press Ctrl+C to stop.\n")

with mouse.Listener(on_click=on_click) as listener:
    try:
        listener.join()
    except KeyboardInterrupt:
        print("\nFinder stopped.")
