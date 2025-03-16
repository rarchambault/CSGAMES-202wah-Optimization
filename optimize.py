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

def find_matching_customer(customer_worder, customers):
    """Find the customer in the customers dictionary based on their Id."""
    # Assuming customers is a dictionary with customer Ids as keys
    customer_id = customer_worder["Id"]
    
    # Check if customer_id exists in the customers dictionary
    matching_customer = customers.get(customer_id)
    
    if matching_customer:
        return matching_customer
    else:
        print(f"No customer found with Id {customer_id}")
        return None

def find_customer_orders_by_customer_id(customer_id, customers_worders):
    """Find a customer by their Id and return their orders."""
    customer = next((c for c in customers_worders if c["Id"] == customer_id), None)
    if customer:
        return customer["Orders"]  # Return the orders of the found customer
    else:
        print(f"No customer found with Id {customer_id}")
        return None

# Function to assign customers to warehouses with knapsack-like optimization
def assign_customers_to_warehouses(day_data, warehouses, customers, warehouse_stocks):
    customer_assignments = {}

    # Sort customers by proximity to warehouses and prioritize based on order size
    for customer in day_data["Customers"]:
        best_warehouse = None
        remaining_orders = customer["Orders"]

        # List all possible warehouses based on available Lego stock
        for order in remaining_orders:
            lego_id = order["LegoId"]
            required_quantity = order["Quantity"]

            # Find warehouses that have enough stock for this order
            possible_warehouses = [
                w for w in day_data["Warehouses"]
                if lego_id in warehouse_stocks[w["Id"]] and warehouse_stocks[w["Id"]][lego_id] >= required_quantity
            ]
            
            if not possible_warehouses:
                print(f"Warning: No warehouse has enough stock for LegoId {lego_id} and quantity {required_quantity}")
                continue

            # Sort the possible warehouses by proximity to the customer
            customer_wcoords = find_matching_customer(customer, customers)
            sorted_warehouses = sorted(
                possible_warehouses, 
                key=lambda w: manhattan_distance(
                    (customer_wcoords["Coordinates"]["X"], customer_wcoords["Coordinates"]["Y"]),
                    (warehouses[w["Id"]]["Coordinates"]["X"], warehouses[w["Id"]]["Coordinates"]["Y"])
                )
            )

            # Try to assign the best warehouse based on proximity and stock availability
            assigned = False
            for warehouse in sorted_warehouses:
                warehouse_id = warehouse["Id"]
                if warehouse_stocks[warehouse_id][lego_id] >= required_quantity:
                    # Assign the warehouse to the customer for this Lego order
                    customer_assignments[customer["Id"]] = warehouse_id

                    # Reduce the stock in the warehouse for this Lego
                    warehouse_stocks[warehouse_id][lego_id] -= required_quantity
                    assigned = True
                    break

            if not assigned:
                print(f"Warning: Couldn't fulfill the order for LegoId {lego_id} and quantity {required_quantity} for customer {customer['Id']}.")

    return customer_assignments


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
        day_number = day_data["DayNumber"]
        steps = []
        
        # Extract locations and stocks
        warehouses = {w["Id"]: w for w in city_layout["Warehouses"]}
        customers = {c["Id"]: c for c in city_layout["Customers"]}
        warehouse_stocks = extract_warehouse_stocks(day_data)
        trucks = day_data["Trucks"]
        
        # Use the optimized customer assignment function
        customer_assignments = assign_customers_to_warehouses(day_data, warehouses, customers, warehouse_stocks)

        # Group customers by warehouse
        warehouse_customer_map = {w_id: [] for w_id in warehouse_stocks.keys()}
        for customer_id, warehouse_id in customer_assignments.items():
            warehouse_customer_map[warehouse_id].append(customer_id)
        
        # Assign trucks to deliveries for each warehouse
        truck_routes = {t["Id"]: [] for t in trucks}
        for warehouse_id, customer_ids in warehouse_customer_map.items():
            assigned_trucks = [t for t in trucks if t["AffiliatedWarehouseId"] == warehouse_id]
            if not assigned_trucks:
                continue
            
            # Balance the load across trucks
            truck_count = len(assigned_trucks)
            customers_per_truck = len(customer_ids) // truck_count
            for i, truck in enumerate(assigned_trucks):
                start_idx = i * customers_per_truck
                end_idx = (i + 1) * customers_per_truck if i < truck_count - 1 else len(customer_ids)
                truck_routes[truck["Id"]] = customer_ids[start_idx:end_idx]
        
        # Perform deliveries
        for truck_id, assigned_customers in truck_routes.items():
            truck = trucks[truck_id]
            warehouse_id = truck["AffiliatedWarehouseId"]
            
            # Collect all orders for the truck and group them by customer
            truck_orders = {}
            for customer_id in assigned_customers:
                orders = next(c["Orders"] for c in day_data["Customers"] if c["Id"] == customer_id)
                for order in orders:
                    if customer_id not in truck_orders:
                        truck_orders[customer_id] = []
                    truck_orders[customer_id].append(order)
            
            # Optimize the truck route to minimize travel time
            customer_coords = [
                (c["Id"], (customers[c["Id"]]["Coordinates"]["X"], customers[c["Id"]]["Coordinates"]["Y"])) 
                for c in day_data["Customers"]
            ]
            
            # Create optimized route for the truck
            optimized_route = nearest_neighbor_path(
                (warehouses[warehouse_id]["Coordinates"]["X"], warehouses[warehouse_id]["Coordinates"]["Y"]),
                [c[1] for c in customer_coords]
            )
            
            # Load all Legos at once for the truck
            for customer_id, orders in truck_orders.items():
                for order in orders:
                    steps.append(f"load truck={truck_id} quantity={order['Quantity']} lego={order['LegoId']}")
            
            # Consolidate the delivery steps into a single trip per customer
            for coords in optimized_route:
                customer = next(c for c in day_data["Customers"] if 
                                (customers[c["Id"]]["Coordinates"]["X"], customers[c["Id"]]["Coordinates"]["Y"]) == coords)
                orders = truck_orders.get(customer["Id"], [])
                if orders:
                    # Move to customer
                    steps.append(f"move_to_customer truck={truck_id} customer={customer['Id']}")
                    
                    # Deliver all orders to that customer at once
                    for order in orders:
                        steps.append(f"deliver truck={truck_id} quantity={order['Quantity']} lego={order['LegoId']}")
            
            # Return truck to warehouse in one final step
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