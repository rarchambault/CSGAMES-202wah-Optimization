import requests
import json
import zipfile
import os

# API Base URL
BASE_URL = "https://opti.csgames.org"

# API Endpoints
DOWNLOAD_DATA_ENDPOINT = "/DownloadData"
SUBMIT_SOLUTION_ENDPOINT = "/Solution"

# Team credentials (update with actual values)
TEAM_CREDENTIALS = {
    "teamName": "McDrill",
    "password": "steep-softly-agree"
}

HEADERS = {
    "Content-Type": "application/json"
}

ZIP_FILE = "challenge_data.zip"
EXTRACTED_FOLDER = "challenge_data"

def download_data():
    """Download the challenge ZIP file and extract it."""
    response = requests.get(BASE_URL + DOWNLOAD_DATA_ENDPOINT, headers=HEADERS)
    
    if response.status_code == 200:
        with open(ZIP_FILE, "wb") as file:
            file.write(response.content)
        print("Challenge data downloaded successfully.")
        
        # Extract ZIP file
        with zipfile.ZipFile(ZIP_FILE, 'r') as zip_ref:
            zip_ref.extractall(EXTRACTED_FOLDER)
        print("Data extracted.")
        return True
    else:
        print("Error downloading data:", response.status_code, response.text)
        return False

def load_json(file_name):
    """Load a JSON file from the extracted data."""
    file_path = os.path.join(EXTRACTED_FOLDER, file_name)
    with open(file_path, "r") as file:
        return json.load(file)

def optimize_delivery_route(day_data, city_layout):
    """Implement a basic delivery route optimization strategy."""
    # TODO: Implement real optimization algorithm
    optimized_solution = {
        "credentials": TEAM_CREDENTIALS,
        "dayNumber": day_data["DayNumber"],
        "steps": []  # Replace with an actual optimized route
    }
    return optimized_solution

def submit_solution(day_number, solution):
    """Submit the optimized solution to the API."""
    response = requests.post(
        f"{BASE_URL}{SUBMIT_SOLUTION_ENDPOINT}",
        json=solution,
        headers=HEADERS
    )
    
    if response.status_code == 200:
        print(f"Solution for day {day_number} submitted successfully!")
        return response.json()
    else:
        print(f"Error submitting solution for day {day_number}:", response.status_code, response.text)
        return None

def main():
    """Main function to execute the challenge."""
    if not download_data():
        return

    # Load city layout
    city_layout = load_json("las_brickas.json")

    # Extract and sort customer coordinates by ID
    sorted_customers = sorted(city_layout["Customers"], key=lambda c: c["Id"])
    coordinates_list = [(c["Coordinates"]["X"], c["Coordinates"]["Y"]) for c in sorted_customers]

    # Solve and submit solutions for the first 3 days
    for day in range(1, 4):
        day_data = load_json(f"day_{day}.json")
        optimized_solution = optimize_delivery_route(day_data, city_layout)
        submit_solution(day, optimized_solution)

    print("Optimization process completed. Keep refining your algorithm!")

if __name__ == "__main__":
    main()