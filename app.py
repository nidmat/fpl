import os
from google import genai
from google.genai import types


def main():
    # Retrieve the API key from environment variables
    # Defaults to os.environ.get("GEMINI_API_KEY") if omitted in Client()
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("Please set the GEMINI_API_KEY environment variable.")

    # Initialize the Gemini client
    client = genai.Client(api_key=api_key)

    # Configure generation settings
    config = types.GenerateContentConfig(
        temperature=0.7,
        max_output_tokens=1024,
        system_instruction="You are a helpful, concise assistant.",
    )

    prompt = "Explain the difference between synchronous and asynchronous programming in 3 sentences."

    print("Sending prompt to Gemini...\n")

    # Generate content using Gemini
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=config,
    )

    # Print response
    print("--- Response ---")
    print(response.text)


if __name__ == "__main__":
    main()
