import requests
import json
import zipfile
import os
import json
import zipfile
import os
from itertools import permutations

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

# Manhattan distance function
def manhattan_distance(p1, p2):
    """Calculate Manhattan distance between two (x, y) points."""
    return abs(p1[0] - p2[0]) + abs(p1[1] - p2[1])

def find_closest_warehouse(customer, warehouses):
    """Find the closest warehouse to a customer based on Manhattan distance."""
    return min(warehouses, key=lambda w: manhattan_distance(
    (w["Coordinates"]["X"], w["Coordinates"]["Y"]), 
    (customer["Coordinates"]["X"], customer["Coordinates"]["Y"])
    ))


def nearest_neighbor_path(start, points):
    """Find a near-optimal order of visiting points using the Nearest Neighbor heuristic."""
    path = [start]
    remaining = points.copy()
    
    while remaining:
        last = path[-1]
        next_point = min(remaining, key=lambda p: manhattan_distance(last, p))
        path.append(next_point)
        remaining.remove(next_point)
    
    return path[1:]  # Remove start point from path

def optimize_delivery_route(day_data, city_layout):
    """Generate an optimized delivery route for a given day."""
    day_number = day_data["DayNumber"]
    steps = []
    
    # Extract locations
    warehouses = {w["Id"]: w for w in city_layout["Warehouses"]}
    customers = {c["Id"]: c for c in city_layout["Customers"]}

    if day_number == 1:
        # **Day 1: Simple Delivery**
        truck = day_data["Trucks"][0]
        warehouse = warehouses[truck["AffiliatedWarehouseId"]]
        customer = list(day_data["Customers"])[0]
        order = customer["Orders"][0]

        # Load, move, deliver, return
        steps.append(f"load truck={truck['Id']} quantity={order['Quantity']} lego={order['LegoId']}")
        steps.append(f"move_to_customer truck={truck['Id']} customer={customer['Id']}")
        steps.append(f"deliver truck={truck['Id']} quantity={order['Quantity']} lego={order['LegoId']}")
        steps.append(f"move_to_warehouse truck={truck['Id']} warehouse={truck['AffiliatedWarehouseId']}")

    elif day_number == 2:
        # **Day 2: Multiple Deliveries, Unlimited Capacity**
        truck = day_data["Trucks"][0]
        warehouse = warehouses[truck["AffiliatedWarehouseId"]]

        # Load everything at once
        for customer in day_data["Customers"]:
            for order in customer["Orders"]:
                steps.append(f"load truck={truck['Id']} quantity={order['Quantity']} lego={order['LegoId']}")

        # Find the shortest path visiting all customers
        customer_coords = [(c["Id"], (customers[c["Id"]]["Coordinates"]["X"], customers[c["Id"]]["Coordinates"]["Y"])) for c in day_data["Customers"]]
        sorted_customers = nearest_neighbor_path(
            (warehouse["Coordinates"]["X"], warehouse["Coordinates"]["Y"]), 
            [c[1] for c in customer_coords]
        )

        # Deliver orders in order
        for coords in sorted_customers:
            customer = next(c for c in day_data["Customers"] if customers[c["Id"]]["Coordinates"] == coords)
            for order in customer["Orders"]:
                steps.append(f"move_to_customer truck={truck['Id']} customer={customer['Id']}")
                steps.append(f"deliver truck={truck['Id']} quantity={order['Quantity']} lego={order['LegoId']}")

        # Return to warehouse
        steps.append(f"move_to_warehouse truck={truck['Id']} warehouse={truck['AffiliatedWarehouseId']}")

    elif day_number == 3:
        # **Day 3: Multiple Warehouses, Multiple Trucks, Limited Capacity**
        trucks = {t["Id"]: t for t in day_data["Trucks"]}
        warehouse_stocks = {w["Id"]: {s["LegoId"]: s["Quantity"] for s in w["Stock"]} for w in day_data["Warehouses"]}

        # Assign customers to the closest warehouse that has their Lego
        customer_assignments = {}
        for customer in day_data["Customers"]:
            best_warehouse = None
            for order in customer["Orders"]:
                possible_warehouses = [w for w in day_data["Warehouses"] if order["LegoId"] in warehouse_stocks[w["Id"]]]
                closest = find_closest_warehouse(customers[customer["Id"]], possible_warehouses)
                best_warehouse = closest["Id"]
            customer_assignments[customer["Id"]] = best_warehouse

        # Assign trucks to deliveries
        truck_routes = {t["Id"]: [] for t in trucks}
        for customer_id, warehouse_id in customer_assignments.items():
            assigned_truck = next((t for t in trucks.values() if t["AffiliatedWarehouseId"] == warehouse_id), None)
            if assigned_truck:
                truck_routes[assigned_truck["Id"]].append(customer_id)

        # Execute deliveries
        for truck_id, assigned_customers in truck_routes.items():
            truck = trucks[truck_id]
            warehouse_id = truck["AffiliatedWarehouseId"]

            # Load necessary Legos
            for customer_id in assigned_customers:
                customer = customers[customer_id]
                for order in customer["Orders"]:
                    steps.append(f"load truck={truck_id} quantity={order['Quantity']} lego={order['LegoId']}")

            # Optimize route using Nearest Neighbor
            customer_coords = [customers[c]["Coordinates"] for c in assigned_customers]
            optimized_route = nearest_neighbor_path(warehouses[warehouse_id]["Coordinates"], customer_coords)

            # Perform deliveries
            for coords in optimized_route:
                customer = next(c for c in day_data["Customers"] if customers[c["Id"]]["Coordinates"] == coords)
                for order in customer["Orders"]:
                    steps.append(f"move_to_customer truck={truck_id} customer={customer['Id']}")
                    steps.append(f"deliver truck={truck_id} quantity={order['Quantity']} lego={order['LegoId']}")

            # Return truck to warehouse
            steps.append(f"move_to_warehouse truck={truck_id} warehouse={warehouse_id}")

    return {
        "credentials": TEAM_CREDENTIALS,
        "dayNumber": day_number,
        "steps": steps
    }

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