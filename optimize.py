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

def find_closest_warehouse(customer, warehouses, city_layout=None):
    """Find the closest warehouse to a customer based on Manhattan distance."""
    
    if city_layout:  # If city_layout is provided (day 3 case), use it to get coordinates
        # Look up coordinates in city_layout for each warehouse
        return min(warehouses, key=lambda w: manhattan_distance(
            (city_layout["Warehouses"][w["Id"]]["Coordinates"]["X"], 
             city_layout["Warehouses"][w["Id"]]["Coordinates"]["Y"]), 
            (customer["Coordinates"]["X"], customer["Coordinates"]["Y"])
        ))
    else:  # If no city_layout, use the Coordinates in day_3.json
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

def merge_customer_data(day_data, city_layout):
    """
    Merges customer order data from day_data with customer details from city_layout
    """
    # Extract orders and customer data from day_data and city_layout
    customers_with_orders = {c["Id"]: c for c in day_data["Customers"]}
    customers_with_details = {c["Id"]: c for c in city_layout["Customers"]}
    
    # Merge the data by matching on customer Id
    merged_customers = {}
    
    for customer_id, customer_data in customers_with_orders.items():
        if customer_id in customers_with_details:
            # Merge the order details with the customer details
            merged_customer = customer_data.copy()
            merged_customer.update(customers_with_details[customer_id])
            merged_customers[customer_id] = merged_customer
        else:
            print(f"Warning: No matching customer details found for customer {customer_id}")
    
    return merged_customers

def extract_warehouse_stocks(day_data):
    """
    Extracts the warehouse stock information from the given day_data.
    
    Args:
    - day_data (dict): The parsed data from the day_3.json file.

    Returns:
    - dict: A dictionary where the key is the warehouse ID and the value is another
            dictionary mapping LegoId to its quantity in that warehouse.
    """
    warehouse_stocks = {}
    
    # Iterate through all warehouses in the data
    for warehouse in day_data["Warehouses"]:
        warehouse_id = warehouse["Id"]
        
        # Create a dictionary for the stock in this warehouse
        stock = {item["LegoId"]: item["Quantity"] for item in warehouse["Stock"]}
        
        # Store it in the main warehouse_stocks dictionary
        warehouse_stocks[warehouse_id] = stock
    
    return warehouse_stocks

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
        customer_coords = [
            (c["Id"], (customers[c["Id"]]["Coordinates"]["X"], customers[c["Id"]]["Coordinates"]["Y"])) 
            for c in day_data["Customers"]
        ]
        sorted_customers = nearest_neighbor_path(
            (warehouse["Coordinates"]["X"], warehouse["Coordinates"]["Y"]), 
            [c[1] for c in customer_coords]
        )

        # Deliver orders in order
        for coords in sorted_customers:
            customer = next(
                c for c in day_data["Customers"] 
                if (customers[c["Id"]]["Coordinates"]["X"], customers[c["Id"]]["Coordinates"]["Y"]) == coords
            )
            for order in customer["Orders"]:
                steps.append(f"move_to_customer truck={truck['Id']} customer={customer['Id']}")
                steps.append(f"deliver truck={truck['Id']} quantity={order['Quantity']} lego={order['LegoId']}")

        # Return to warehouse
        steps.append(f"move_to_warehouse truck={truck['Id']} warehouse={truck['AffiliatedWarehouseId']}")

    elif day_number == 3:
        # **Day 3: Multiple Warehouses, Multiple Trucks, Limited Capacity**
        trucks = day_data["Trucks"]
        truck_routes = {t["Id"]: [] for t in trucks}
        warehouse_stocks = extract_warehouse_stocks(day_data)
        
        # Assign customers to the closest warehouse based on their orders and available Legos
        customer_assignments = {}
        for customer in customers.values():
            if "Orders" in customer:
                best_warehouse = None
                for order in customer["Orders"]:
                    # Find the best warehouse with the Lego stock needed for the order
                    possible_warehouses = [
                        w for w in day_data["Warehouses"] if order["LegoId"] in warehouse_stocks[w["Id"]]
                    ]
                    closest = find_closest_warehouse(customer, possible_warehouses, city_layout)
                    best_warehouse = closest["Id"]
                customer_assignments[customer["Id"]] = best_warehouse
            else:
                print(f"Warning: Customer {customer['Id']} has no orders!")

        # Now assign trucks to deliveries, balancing the load and minimizing distance
        for customer_id, warehouse_id in customer_assignments.items():
            assigned_trucks = [t for t in trucks.values() if t["AffiliatedWarehouseId"] == warehouse_id]
            if assigned_trucks:
                # For simplicity, choose the first truck available for this warehouse
                truck_routes[assigned_trucks[0]["Id"]].append(customer_id)

        # Perform the deliveries
        for truck_id, assigned_customers in truck_routes.items():
            truck = trucks[truck_id]
            warehouse_id = truck["AffiliatedWarehouseId"]

            # Load the necessary Lego quantities onto the truck
            for customer_id in assigned_customers:
                customer = customers[customer_id]
                if "Orders" in customer:
                    for order in customer["Orders"]:
                        steps.append(f"load truck={truck_id} quantity={order['Quantity']} lego={order['LegoId']}")
                else:
                    print(f"Warning: Customer {customer_id} has no orders!")

            # Use Nearest Neighbor or similar algorithm to optimize route
            customer_coords = [
                (c["Id"], (c["Coordinates"]["X"], c["Coordinates"]["Y"])) 
                for c in customers.values()
            ]
            optimized_route = nearest_neighbor_path(
                (warehouses[warehouse_id]["Coordinates"]["X"], warehouses[warehouse_id]["Coordinates"]["Y"]),
                [c[1] for c in customer_coords]
            )

            # Perform deliveries and return truck to warehouse
            for coords in optimized_route:
                customer = next(
                    c for c in customers.values() 
                    if (c["Coordinates"]["X"], c["Coordinates"]["Y"]) == coords
                )
                if "Orders" in customer:
                    for order in customer["Orders"]:
                        steps.append(f"move_to_customer truck={truck_id} customer={customer['Id']}")
                        steps.append(f"deliver truck={truck_id} quantity={order['Quantity']} lego={order['LegoId']}")
                else:
                    print(f"Warning: Customer {customer['Id']} has no orders!")

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

    print("Optimization process completed.")

if __name__ == "__main__":
    main()