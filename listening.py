import speech_recognition as sr
import time

def real_time_speech_to_text():
    # Initialize the recognizer
    recognizer = sr.Recognizer()
    
    # Open the microphone stream
    with sr.Microphone() as source:
        print("Adjusting for ambient noise... Please wait")
        recognizer.adjust_for_ambient_noise(source)  # Adjust for noise levels
        
        print("Listening for speech...")

        try:
            # Continuous listening loop
            while True:
                # Capture audio from the microphone with more context time
                audio = recognizer.listen(source, phrase_time_limit=5)  # Adjust the phrase time limit
                
                try:
                    # Recognize speech using Google Web Speech API
                    text = recognizer.recognize_google(audio)
                    
                    # Split the recognized text into words
                    words = text.split()
                    
                    # Print each word as it is transcribed
                    for word in words:
                        print(word, end=" ", flush=True)
                    
                    # Add a small delay before next recognition to avoid overlapping inputs
                    time.sleep(1)  # Adjust the sleep time as per your need
                
                except sr.UnknownValueError:
                    # Handle cases where speech was not understood
                    print("\n[Unrecognized speech or silence]", end=" ", flush=True)
                
                except sr.RequestError as e:
                    # Handle network issues or API unavailability
                    print(f"\n[API unavailable or network error: {str(e)}] - Switching to offline recognition", end=" ", flush=True)
                    try:
                        # Fallback to offline speech recognition (CMU Sphinx)
                        text = recognizer.recognize_sphinx(audio)
                        words = text.split()
                        for word in words:
                            print(word, end=" ", flush=True)
                    except sr.UnknownValueError:
                        print("\n[Unrecognized speech or silence - even with offline mode]", end=" ", flush=True)
                    except sr.RequestError:
                        print("\n[Offline recognition is not supported or failed]", end=" ", flush=True)

        except KeyboardInterrupt:
            print("\nStopping transcription.")
            
# Run the real-time speech-to-text function
real_time_speech_to_text()
