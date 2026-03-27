import cv2
import sys
import os
import time

# Add the project root to sys.path so we can import services
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.proctoring.proctoring_system import analyze_frame

def main():
    print("Starting webcam... Press 'q' to quit.")
    # Initialize webcam
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("Error: Could not open webcam.")
        return

    # Brief pause to let the camera warm up
    time.sleep(1)

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Error: Failed to capture image.")
            break

        # Flip horizontally for an intuitive mirror view
        frame = cv2.flip(frame, 1)

        # Pass through the updated proctoring logic
        annotated_frame, status, head_pos = analyze_frame(frame)

        # Overlay status text
        color = (0, 255, 0) if head_pos == "Center" else (0, 0, 255)
        cv2.putText(annotated_frame, f"Head Position: {head_pos}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
        cv2.putText(annotated_frame, f"System Status: {status}", (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
        cv2.putText(annotated_frame, "Press 'q' to exit", (10, 90),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        # Render window
        cv2.imshow("SmartStudy Proctoring Demo", annotated_frame)

        # Quit on 'q'
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # Cleanup
    cap.release()
    cv2.destroyAllWindows()
    print("Demo ended gracefully.")

if __name__ == "__main__":
    main()
